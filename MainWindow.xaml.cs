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

namespace LiveTranslateTool
{
    public partial class MainWindow : System.Windows.Window
    {
        private VideoCapture _capture;
        private DispatcherTimer _timer;
        private readonly HttpClient _httpClient = new HttpClient();
        private const string GoogleTranslateApiKey = "REPLACE WITH API KEY";
        private ListBox _deviceSelector;
        private Canvas _overlayCanvas;
        private List<System.Windows.Rect> _textRegions = new List<System.Windows.Rect>();
        private string _lastExtractedText = "";
        private List<string> _deviceNames = new List<string>();

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
            MainGrid.Children.Add(_deviceSelector);
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

            // Automatically set to best supported format
            SetBestSupportedResolution(deviceIndex);

            _overlayCanvas = new Canvas { IsHitTestVisible = false };
            Panel.SetZIndex(_overlayCanvas, 1);
            MainGrid.Children.Add(_overlayCanvas);

            _timer = new DispatcherTimer
            {
                Interval = TimeSpan.FromMilliseconds(16)
            };
            _timer.Tick += CaptureFrame;
            _timer.Start();
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
            using var frame = new Mat();
            _capture.Read(frame);
            if (frame.Empty()) return;

            var bitmap = BitmapSourceConverter.ToBitmapSource(frame);
            VideoImage.Source = bitmap;
            _overlayCanvas.Children.Clear();

            var tempPath = System.IO.Path.Combine(System.IO.Path.GetTempPath(), Guid.NewGuid() + ".png");
            frame.SaveImage(tempPath);

            string extractedText = await Task.Run(() => ExtractText(tempPath, out _textRegions));

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

        private string ExtractText(string imagePath, out List<System.Windows.Rect> regions)
        {
            regions = new List<System.Windows.Rect>();
            using var engine = new TesseractEngine("./tessdata", "jpn", EngineMode.Default);
            using var img = Pix.LoadFromFile(imagePath);
            using var page = engine.Process(img);

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

        private async Task<string> TranslateText(string input)
        {
            var url =
                $"https://translation.googleapis.com/language/translate/v2?key={GoogleTranslateApiKey}";
            var data = new StringContent($"q={Uri.EscapeDataString(input)}&source=ja&target=en&format=text",
                System.Text.Encoding.UTF8, "application/x-www-form-urlencoded");

            var response = await _httpClient.PostAsync(url, data);
            var result = await response.Content.ReadAsStringAsync();
            var json = JObject.Parse(result);
            return json["data"]?["translations"]?[0]?["translatedText"]?.ToString() ?? "";
        }
    }
}