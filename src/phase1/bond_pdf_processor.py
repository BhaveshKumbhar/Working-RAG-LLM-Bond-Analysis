# bond_pdf_processor.py - FIXED with robust OCR error handling

import PyPDF2
import pytesseract
from PIL import Image
import cv2
import numpy as np
import os
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
import re
import warnings

# Try to set tesseract path (Windows)
try:
    pytesseract.pytesseract.pytesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'
except:
    pass

@dataclass
class ExtractedPage:
    """Single page extraction with metadata"""
    page_number: int
    text_content: str
    extracted_images: List[str]  # OCR text from images
    has_images: bool
    image_confidence: Optional[float] = None
    source: str = "combined"  # text, ocr, or combined

class BondPDFProcessor:
    """Extract and process Bond PDF with OCR support"""
    
    def __init__(self, pdf_path: str, output_dir: str = "bond_output"):
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.tesseract_available = self._check_tesseract()
        
        if not self.tesseract_available:
            print("⚠️  WARNING: Tesseract OCR not available. Images will be skipped.")
            print("   To enable OCR, install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")
    
    def _check_tesseract(self) -> bool:
        """Check if tesseract is available"""
        try:
            pytesseract.get_tesseract_version()
            return True
        except:
            return False
    
    def extract_text_from_pdf(self) -> Dict[int, str]:
        """Extract text from PDF pages"""
        print("📄 Extracting text from PDF...")
        
        text_by_page = {}
        
        with open(self.pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                text_by_page[page_num + 1] = text if text else ""
                
                if (page_num + 1) % 5 == 0:
                    print(f"  Processed {page_num + 1}/{total_pages} pages")
        
        print(f"✅ Text extraction complete: {total_pages} pages")
        return text_by_page
    
    def extract_images_from_pdf(self) -> Dict[int, List[Image.Image]]:
        """Extract images from PDF pages"""
        print("🖼️  Extracting images from PDF...")
        
        images_by_page = {}
        
        with open(self.pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            image_count = 0
            
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                images = []
                
                if "/XObject" in page["/Resources"]:
                    xobject = page["/Resources"]["/XObject"].get_object()
                    
                    for obj in xobject:
                        if xobject[obj]["/Subtype"] == "/Image":
                            try:
                                size = (xobject[obj]["/Width"], xobject[obj]["/Height"])
                                data = xobject[obj].get_data()
                                
                                if xobject[obj]["/ColorSpace"] == "/DeviceRGB":
                                    image = Image.new("RGB", size)
                                else:
                                    image = Image.new("L", size)
                                
                                image.frombytes(data)
                                images.append(image)
                                image_count += 1
                            except:
                                pass
                
                if images:
                    images_by_page[page_num + 1] = images
        
        print(f"✅ Image extraction complete: {image_count} images found")
        return images_by_page
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results"""
        try:
            # Convert to numpy array
            img_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Grayscale
            gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
            
            # Denoising
            denoised = cv2.fastNlMeansDenoising(gray, h=10)
            
            # Thresholding for better contrast
            _, binary = cv2.threshold(denoised, 150, 255, cv2.THRESH_BINARY)
            
            # Upscale for better OCR (3x)
            scaled = cv2.resize(binary, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            
            return Image.fromarray(scaled)
        except Exception as e:
            print(f"    ⚠️  Image preprocessing failed: {str(e)}")
            return image
    
    def ocr_image(self, image: Image.Image) -> Tuple[str, float]:
        """Run OCR on image and return text + confidence"""
        if not self.tesseract_available:
            return "", 0.0
        
        try:
            # Preprocess
            processed_image = self.preprocess_image(image)
            
            # Run OCR with confidence
            data = pytesseract.image_to_data(processed_image, output_type=pytesseract.Output.DICT)
            
            # Extract text and calculate confidence
            text = pytesseract.image_to_string(processed_image)
            
            # Average confidence (0-100)
            confidences = [int(conf) for conf in data['confidence'] if int(conf) > 0]
            avg_confidence = np.mean(confidences) / 100.0 if confidences else 0.0
            
            return text, avg_confidence
        
        except pytesseract.TesseractNotFoundError:
            print(f"    ⚠️  Tesseract not found in PATH")
            return "", 0.0
        except Exception as e:
            print(f"    ⚠️  OCR Error: {str(e)}")
            return "", 0.0
    
    def extract_images_and_ocr(self) -> Dict[int, Tuple[str, float]]:
        """Extract and OCR all images"""
        if not self.tesseract_available:
            print("🔍 Skipping OCR (Tesseract not available)")
            return {}
        
        print("🔍 Running OCR on extracted images...")
        
        images_by_page = self.extract_images_from_pdf()
        ocr_results = {}
        
        total_images = sum(len(imgs) for imgs in images_by_page.values())
        processed = 0
        successful = 0
        failed = 0
        
        for page_num, images in images_by_page.items():
            ocr_texts = []
            confidences = []
            
            for image in images:
                try:
                    text, confidence = self.ocr_image(image)
                    if text.strip():
                        ocr_texts.append(text)
                        confidences.append(confidence)
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    print(f"    ⚠️  Failed to OCR image: {str(e)}")
                    failed += 1
                
                processed += 1
                
                if processed % 5 == 0:
                    print(f"  Processed {processed}/{total_images} images (✅ {successful}, ❌ {failed})")
            
            if ocr_texts:
                combined_text = "\n".join(ocr_texts)
                avg_confidence = np.mean(confidences) if confidences else 0.0
                ocr_results[page_num] = (combined_text, avg_confidence)
        
        print(f"✅ OCR complete: {len(ocr_results)} pages with OCR results")
        print(f"   Images processed: {successful}/{total_images} successful, {failed} failed")
        
        return ocr_results
    
    def merge_text_and_ocr(self, 
                          text_by_page: Dict[int, str], 
                          ocr_results: Dict[int, Tuple[str, float]]) -> Dict[int, ExtractedPage]:
        """Merge extracted text and OCR results"""
        print("🔗 Merging text and OCR results...")
        
        merged_pages = {}
        
        for page_num, text in text_by_page.items():
            extracted_images = []
            image_confidence = None
            has_images = False
            
            if page_num in ocr_results:
                ocr_text, confidence = ocr_results[page_num]
                extracted_images = [ocr_text]
                image_confidence = confidence
                has_images = True
                
                # Merge: prioritize native text, append OCR if low confidence text
                if len(text.strip()) < 50:  # Very little native text
                    combined_text = text + "\n[OCR EXTRACTED TEXT]\n" + ocr_text
                    source = "ocr"
                else:
                    combined_text = text + "\n[OCR SUPPLEMENTARY TEXT]\n" + ocr_text
                    source = "combined"
            else:
                combined_text = text
                source = "text"
            
            page = ExtractedPage(
                page_number=page_num,
                text_content=combined_text,
                extracted_images=extracted_images,
                has_images=has_images,
                image_confidence=image_confidence,
                source=source
            )
            
            merged_pages[page_num] = page
        
        print(f"✅ Merging complete: {len(merged_pages)} pages processed")
        return merged_pages

# Usage
if __name__ == "__main__":
    processor = BondPDFProcessor("bond_memorandum.pdf")
    
    # Extract text
    text_by_page = processor.extract_text_from_pdf()
    
    # Extract and OCR images
    ocr_results = processor.extract_images_and_ocr()
    
    # Merge results
    merged_pages = processor.merge_text_and_ocr(text_by_page, ocr_results)
    
    print(f"\n📊 Summary:")
    print(f"  Total pages: {len(merged_pages)}")
    print(f"  Pages with OCR: {sum(1 for p in merged_pages.values() if p.has_images)}")