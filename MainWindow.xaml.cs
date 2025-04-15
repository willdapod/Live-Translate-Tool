using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Effects;
using System.Windows.Media.Imaging;
using OpenCvSharp;
using OpenCvSharp.Extensions;
using System.IO;
using System.Windows.Shapes;
using System.Windows.Threading;
using Tesseract;
using System.Net.Http;
using Newtonsoft.Json.Linq;
using System.Runtime.InteropServices;
using DirectShowLib;
using OpenCvSharp.WpfExtensions;
using System.Drawing;
using Color = System.Windows.Media.Color;
using Brushes = System.Windows.Media.Brushes;
using System.Threading;

namespace LiveTranslateTool
{
    public partial class MainWindow : System.Windows.Window
    {
        private VideoCapture _capture; 
        private CancellationTokenSource _cancellationTokenSource;
        private readonly HttpClient _httpClient = new HttpClient();
        private ListBox _deviceSelector;
        private Canvas _overlayCanvas;
        private List<System.Windows.Rect> _textRegions = new List<System.Windows.Rect>();
        private string _lastExtractedText = "";
        private List<string> _deviceNames = new List<string>();
        private Dictionary<string, string> _translationCache = new Dictionary<string, string>();
        private int _frameCounter = 0;  // Counter to process every nth frame

        public MainWindow()
        {
            InitializeComponent();
            Loaded += MainWindow_Loaded;
        }

        private void MainWindow_Loaded(object sender, RoutedEventArgs e)
        {
            _deviceSelector = new ListBox { Margin = new Thickness(10) };

            var systemCameras = new DsDevice[0];
            try
            {
                systemCameras = DsDevice.GetDevicesOfCat(FilterCategory.VideoInputDevice);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error accessing capture devices: {ex.Message}");
                return;
            }

            for (int i = 0; i < systemCameras.Length; i++)
            {
                using var temp = new VideoCapture(i);
                if (temp.IsOpened())
                {
                    string name = systemCameras[i].Name;
                    _deviceNames.Add(name);
                    _deviceSelector.Items.Add(new ComboBoxItem { Content = name, Tag = i });
                }
            }

            if (_deviceSelector.Items.Count == 0)
            {
                MessageBox.Show("No video capture devices found.");
                return;
            }

            _deviceSelector.SelectionChanged += DeviceSelector_SelectionChanged;
            TopBar.Children.Add(_deviceSelector);
        }

        private void DeviceSelector_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (_deviceSelector.SelectedItem is ComboBoxItem item && item.Tag is int index)
            {
                MainGrid.Children.Remove(_deviceSelector);
                StartCapture(index);
            }
        }
        private void StartCapture(int deviceIndex)
        {
            _capture = new VideoCapture(deviceIndex);
            SetBestSupportedResolution(deviceIndex);

            _overlayCanvas = new Canvas { IsHitTestVisible = false };
            Panel.SetZIndex(_overlayCanvas, 1);
            MainGrid.Children.Add(_overlayCanvas);

            _cancellationTokenSource = new CancellationTokenSource();
            Task.Run(() => CaptureLoop(_cancellationTokenSource.Token));
        }

        private void StopCapture()
        {
            _cancellationTokenSource?.Cancel();
            _capture?.Release();
            _capture?.Dispose();
        }

        private async Task CaptureLoop(CancellationToken token)
        {
            while (!token.IsCancellationRequested)
            {
                using var frame = new Mat();
                _capture.Read(frame);

                if (!frame.Empty())
                {
                    var bitmap = frame.ToBitmapSource();
                    bitmap.Freeze(); // Allows cross-thread access

                    Dispatcher.Invoke(() =>
                    {
                        VideoImage.Source = bitmap;
                        _overlayCanvas.Children.Clear();
                    });

                    if (_frameCounter++ % 5 == 0)
                    {
                        string extractedText = await Task.Run(() => ExtractTextFromMat(frame, out _textRegions));
                        if (!string.IsNullOrWhiteSpace(extractedText) && extractedText != _lastExtractedText)
                        {
                            _lastExtractedText = extractedText;
                            string translated = await TranslateText(extractedText);

                            Dispatcher.Invoke(() =>
                            {
                                foreach (var region in _textRegions)
                                {
                                    var tb = new TextBlock
                                    {
                                        Text = translated,
                                        Foreground = Brushes.White,
                                        Background = new SolidColorBrush(Color.FromArgb(180, 0, 0, 0)),
                                        FontSize = 16,
                                        Padding = new Thickness(4),
                                        TextWrapping = TextWrapping.Wrap,
                                        Effect = new BlurEffect { Radius = 1.5 }
                                    };
                                    Canvas.SetLeft(tb, region.X);
                                    Canvas.SetTop(tb, region.Y);
                                    _overlayCanvas.Children.Add(tb);
                                }
                            });
                        }
                    }
                }

                await Task.Delay(10); // Add small delay to prevent CPU hogging
            }
        }

        private void SetBestSupportedResolution(int index)
        {
            try
            {
                var devices = DsDevice.GetDevicesOfCat(FilterCategory.VideoInputDevice);
                var dev = devices[index];

                var filterGraph = (IFilterGraph2)new FilterGraph();
                filterGraph.AddSourceFilterForMoniker(dev.Mon, null, dev.Name, out IBaseFilter sourceFilter);

                var config = sourceFilter as IAMStreamConfig;
                if (config == null)
                {
                    filterGraph.RemoveFilter(sourceFilter);
                    return;
                }

                config.GetNumberOfCapabilities(out int count, out int size);
                var ptr = Marshal.AllocCoTaskMem(size);

                int bestWidth = 0, bestHeight = 0, bestFps = 0;

                for (int i = 0; i < count; i++)
                {
                    config.GetStreamCaps(i, out AMMediaType mediaType, ptr);
                    var v = (VideoInfoHeader)Marshal.PtrToStructure(mediaType.formatPtr, typeof(VideoInfoHeader));

                    int width = v.BmiHeader.Width;
                    int height = v.BmiHeader.Height;
                    int fps = (int)(10000000.0 / v.AvgTimePerFrame);

                    if ((width * height > bestWidth * bestHeight) || (width == bestWidth && height == bestHeight && fps > bestFps))
                    {
                        bestWidth = width;
                        bestHeight = height;
                        bestFps = fps;
                    }

                    DsUtils.FreeAMMediaType(mediaType);
                }

                Marshal.FreeCoTaskMem(ptr);

                _capture.Set(VideoCaptureProperties.FrameWidth, bestWidth);
                _capture.Set(VideoCaptureProperties.FrameHeight, bestHeight);
                _capture.Set(VideoCaptureProperties.Fps, bestFps);

                Console.WriteLine($"Set to: {bestWidth}x{bestHeight} @ {bestFps}fps");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Resolution detect failed: {ex.Message}");
            }
        }

        private async void CaptureFrame(object sender, EventArgs e)
        {
            if (_frameCounter % 5 != 0)  // Process every 5th frame
            {
                _frameCounter++;
                return;
            }
            _frameCounter++;

            using var frame = new Mat();
            _capture.Read(frame);
            if (frame.Empty()) return;

            var bitmap = BitmapSourceConverter.ToBitmapSource(frame);
            VideoImage.Source = bitmap;
            _overlayCanvas.Children.Clear();

            string extractedText = await Task.Run(() => ExtractTextFromMat(frame, out _textRegions));

            if (!string.IsNullOrWhiteSpace(extractedText) && extractedText != _lastExtractedText)
            {
                _lastExtractedText = extractedText;
                string translated = await TranslateText(extractedText);
                foreach (var region in _textRegions)
                {
                    var tb = new TextBlock
                    {
                        Text = translated,
                        Foreground = Brushes.White,
                        Background = new SolidColorBrush(Color.FromArgb(180, 0, 0, 0)),
                        FontSize = 16,
                        Padding = new Thickness(4),
                        TextWrapping = TextWrapping.Wrap,
                        Effect = new BlurEffect { Radius = 1.5 }
                    };
                    Canvas.SetLeft(tb, region.X);
                    Canvas.SetTop(tb, region.Y);
                    _overlayCanvas.Children.Add(tb);
                }
            }
        }

        private string ExtractTextFromMat(Mat frame, out List<System.Windows.Rect> regions)
        {
            regions = new List<System.Windows.Rect>();

            // Convert Mat to Bitmap
            Bitmap bitmap = frame.ToBitmap();

            // Convert Bitmap to Pix (Tesseract compatible)
            using var pix = Pix.LoadFromMemory(BitmapToByteArray(bitmap));

            using var engine = new TesseractEngine("./tessdata", "jpn", EngineMode.Default);
            using var page = engine.Process(pix);  // Use Pix for processing

            var text = page.GetText();

            using (var iter = page.GetIterator())
            {
                iter.Begin();
                do
                {
                    if (iter.TryGetBoundingBox(PageIteratorLevel.Word, out var bbox))
                    {
                        regions.Add(new System.Windows.Rect(bbox.X1, bbox.Y1, bbox.Width, bbox.Height));
                    }
                } while (iter.Next(PageIteratorLevel.Word));
            }

            return text.Trim();
        }

        private byte[] BitmapToByteArray(Bitmap bitmap)
        {
            using (MemoryStream stream = new MemoryStream())
            {
                bitmap.Save(stream, System.Drawing.Imaging.ImageFormat.Png);
                return stream.ToArray();
            }
        }



        private async Task<string> TranslateText(string input)
        {
            if (_translationCache.ContainsKey(input))
            {
                return _translationCache[input];  // Return cached translation
            }

            var url = "https://libretranslate.com/translate";
            var data = new
            {
                q = input,
                source = "ja",
                target = "en",
                format = "text"
            };

            var jsonData = Newtonsoft.Json.JsonConvert.SerializeObject(data);
            var content = new StringContent(jsonData, System.Text.Encoding.UTF8, "application/json");

            var response = await _httpClient.PostAsync(url, content);
            var result = await response.Content.ReadAsStringAsync();
            var jsonResponse = JObject.Parse(result);

            var translatedText = jsonResponse["translatedText"]?.ToString() ?? "";
            _translationCache[input] = translatedText;  // Cache the result
            return translatedText;
        }

        private async void LoadTestImage_Click(object sender, RoutedEventArgs e)
        {
            var dialog = new Microsoft.Win32.OpenFileDialog
            {
                Filter = "Image Files|*.jpg;*.jpeg;*.png;*.bmp"
            };

            if (dialog.ShowDialog() == true)
            {
                try
                {
                    // Load the image into a Mat
                    using var mat = Cv2.ImRead(dialog.FileName);
                    if (mat.Empty())
                    {
                        MessageBox.Show("Could not load image.");
                        return;
                    }

                    // Display image
                    var bitmap = mat.ToBitmapSource();
                    bitmap.Freeze();
                    VideoImage.Source = bitmap;

                    _overlayCanvas?.Children.Clear();
                    if (_overlayCanvas == null)
                    {
                        _overlayCanvas = new Canvas { IsHitTestVisible = false };
                        Panel.SetZIndex(_overlayCanvas, 1);
                        MainGrid.Children.Add(_overlayCanvas);
                    }

                    // OCR and Translate
                    string extractedText = await Task.Run(() => ExtractTextFromMat(mat, out _textRegions));
                    if (!string.IsNullOrWhiteSpace(extractedText))
                    {
                        string translated = await TranslateText(extractedText);

                        foreach (var region in _textRegions)
                        {
                            var tb = new TextBlock
                            {
                                Text = translated,
                                Foreground = Brushes.White,
                                Background = new SolidColorBrush(Color.FromArgb(180, 0, 0, 0)),
                                FontSize = 16,
                                Padding = new Thickness(4),
                                TextWrapping = TextWrapping.Wrap,
                                Effect = new BlurEffect { Radius = 1.5 }
                            };
                            Canvas.SetLeft(tb, region.X);
                            Canvas.SetTop(tb, region.Y);
                            _overlayCanvas.Children.Add(tb);
                        }
                    }
                }
                catch (Exception ex)
                {
                    MessageBox.Show("Error processing image: " + ex.Message);
                }
            }
        }
    }
}
