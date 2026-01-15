import argostranslate.package
import argostranslate.translate
import sys

def install_languages():
    print("Updating package index...")
    argostranslate.package.update_package_index()
    
    available_packages = argostranslate.package.get_available_packages()
    
    # Install Japanese -> English
    package_to_install = next(
        filter(
            lambda x: x.from_code == "ja" and x.to_code == "en", available_packages
        ), None
    )
    
    if package_to_install:
        print(f"Downloading and installing: {package_to_install}")
        argostranslate.package.install_from_path(package_to_install.download())
        print("Done.")
    else:
        print("Could not find Japanese -> English package.")

if __name__ == "__main__":
    install_languages()
