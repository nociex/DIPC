"""Tests for document preprocessing pipeline."""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import json

from src.document.preprocessing import (
    DocumentPreprocessor,
    ProcessedDocument,
    DocumentFormat
)


class TestDocumentPreprocessor:
    """Test cases for DocumentPreprocessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.preprocessor = DocumentPreprocessor()
    
    def test_detect_format_from_content_type(self):
        """Test format detection from content type."""
        # Test image detection
        assert self.preprocessor.detect_format("test.jpg", "image/jpeg") == DocumentFormat.IMAGE
        assert self.preprocessor.detect_format("test.png", "image/png") == DocumentFormat.IMAGE
        
        # Test PDF detection
        assert self.preprocessor.detect_format("test.pdf", "application/pdf") == DocumentFormat.PDF
        
        # Test DOCX detection
        assert self.preprocessor.detect_format(
            "test.docx", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ) == DocumentFormat.DOCX
        
        # Test XLSX detection
        assert self.preprocessor.detect_format(
            "test.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ) == DocumentFormat.XLSX
        
        # Test text detection
        assert self.preprocessor.detect_format("test.txt", "text/plain") == DocumentFormat.TEXT
    
    def test_detect_format_from_filename(self):
        """Test format detection from filename extension."""
        # Test various image formats
        assert self.preprocessor.detect_format("test.jpg") == DocumentFormat.IMAGE
        assert self.preprocessor.detect_format("test.jpeg") == DocumentFormat.IMAGE
        assert self.preprocessor.detect_format("test.png") == DocumentFormat.IMAGE
        assert self.preprocessor.detect_format("test.gif") == DocumentFormat.IMAGE
        
        # Test document formats
        assert self.preprocessor.detect_format("test.pdf") == DocumentFormat.PDF
        assert self.preprocessor.detect_format("test.docx") == DocumentFormat.DOCX
        assert self.preprocessor.detect_format("test.xlsx") == DocumentFormat.XLSX
        assert self.preprocessor.detect_format("test.txt") == DocumentFormat.TEXT
        assert self.preprocessor.detect_format("test.md") == DocumentFormat.TEXT
        
        # Test unknown format
        assert self.preprocessor.detect_format("test.unknown") == DocumentFormat.UNKNOWN
    
    @patch('src.document.preprocessing.requests.get')
    def test_download_file_success(self, mock_get):
        """Test successful file download."""
        # Mock response
        mock_response = Mock()
        mock_response.headers = {
            'content-type': 'application/pdf',
            'content-length': '1024'
        }
        mock_response.iter_content.return_value = [b'test content']
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        file_url = "https://example.com/test.pdf"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            preprocessor = DocumentPreprocessor(temp_dir)
            local_path, content_type = preprocessor.download_file(file_url)
            
            assert content_type == 'application/pdf'
            assert os.path.exists(local_path)
            assert local_path.startswith(temp_dir)
            
            # Clean up
            os.unlink(local_path)
    
    @patch('src.document.preprocessing.requests.get')
    def test_download_file_failure(self, mock_get):
        """Test file download failure."""
        mock_get.side_effect = Exception("Network error")
        
        file_url = "https://example.com/test.pdf"
        
        with pytest.raises(Exception, match="File download failed"):
            self.preprocessor.download_file(file_url)
    
    def test_process_text_file(self):
        """Test processing of text files."""
        test_content = "This is a test document.\nWith multiple lines.\nAnd some content."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            result = self.preprocessor.process_text(temp_path)
            
            assert isinstance(result, ProcessedDocument)
            assert result.format == DocumentFormat.TEXT
            assert result.text_content == test_content
            assert result.metadata['line_count'] == 3
            assert result.metadata['character_count'] == len(test_content)
            assert result.metadata['encoding'] == 'utf-8'
            assert result.file_size > 0
            
        finally:
            os.unlink(temp_path)
    
    def test_process_text_file_encoding_fallback(self):
        """Test text file processing with encoding fallback."""
        # Create file with latin-1 encoding
        test_content = "Café résumé naïve"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='latin-1') as f:
            f.write(test_content)
            temp_path = f.name
        
        try:
            result = self.preprocessor.process_text(temp_path)
            
            assert isinstance(result, ProcessedDocument)
            assert result.format == DocumentFormat.TEXT
            assert result.metadata['encoding'] in ['utf-8', 'latin-1']
            
        finally:
            os.unlink(temp_path)
    
    @patch('src.document.preprocessing.PyPDF2.PdfReader')
    def test_process_pdf_success(self, mock_pdf_reader):
        """Test successful PDF processing."""
        # Mock PDF reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "Test page content"
        
        mock_reader_instance = Mock()
        mock_reader_instance.pages = [mock_page, mock_page]
        mock_reader_instance.metadata = {
            '/Title': 'Test Document',
            '/Author': 'Test Author'
        }
        
        mock_pdf_reader.return_value = mock_reader_instance
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'fake pdf content')
            temp_path = f.name
        
        try:
            result = self.preprocessor.process_pdf(temp_path)
            
            assert isinstance(result, ProcessedDocument)
            assert result.format == DocumentFormat.PDF
            assert "Test page content" in result.text_content
            assert result.metadata['page_count'] == 2
            assert result.metadata['title'] == 'Test Document'
            assert result.metadata['author'] == 'Test Author'
            
        finally:
            os.unlink(temp_path)
    
    @patch('src.document.preprocessing.Image.open')
    @patch('src.document.preprocessing.pytesseract.image_to_string')
    def test_process_image_with_ocr(self, mock_ocr, mock_image_open):
        """Test image processing with OCR."""
        # Mock PIL Image
        mock_img = Mock()
        mock_img.width = 800
        mock_img.height = 600
        mock_img.format = 'JPEG'
        mock_img.mode = 'RGB'
        mock_image_open.return_value.__enter__.return_value = mock_img
        
        # Mock OCR
        mock_ocr.return_value = "Extracted text from image"
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake image content')
            temp_path = f.name
        
        try:
            result = self.preprocessor.process_image(temp_path)
            
            assert isinstance(result, ProcessedDocument)
            assert result.format == DocumentFormat.IMAGE
            assert result.text_content == "Extracted text from image"
            assert result.metadata['width'] == 800
            assert result.metadata['height'] == 600
            assert result.metadata['ocr_extracted'] is True
            assert len(result.image_paths) == 1
            assert result.image_paths[0] == temp_path
            
        finally:
            os.unlink(temp_path)
    
    @patch('src.document.preprocessing.Image.open')
    @patch('src.document.preprocessing.pytesseract.image_to_string')
    def test_process_image_ocr_failure(self, mock_ocr, mock_image_open):
        """Test image processing when OCR fails."""
        # Mock PIL Image
        mock_img = Mock()
        mock_img.width = 800
        mock_img.height = 600
        mock_img.format = 'JPEG'
        mock_img.mode = 'RGB'
        mock_image_open.return_value.__enter__.return_value = mock_img
        
        # Mock OCR failure
        mock_ocr.side_effect = Exception("OCR failed")
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake image content')
            temp_path = f.name
        
        try:
            result = self.preprocessor.process_image(temp_path)
            
            assert isinstance(result, ProcessedDocument)
            assert result.format == DocumentFormat.IMAGE
            assert result.text_content == ""
            assert result.metadata['ocr_extracted'] is False
            assert 'ocr_error' in result.metadata
            
        finally:
            os.unlink(temp_path)
    
    @patch('src.document.preprocessing.DocxDocument')
    def test_process_docx(self, mock_docx):
        """Test DOCX processing."""
        # Mock DOCX document
        mock_paragraph1 = Mock()
        mock_paragraph1.text = "First paragraph"
        mock_paragraph2 = Mock()
        mock_paragraph2.text = "Second paragraph"
        
        mock_cell1 = Mock()
        mock_cell1.text = "Cell 1"
        mock_cell2 = Mock()
        mock_cell2.text = "Cell 2"
        
        mock_row = Mock()
        mock_row.cells = [mock_cell1, mock_cell2]
        
        mock_table = Mock()
        mock_table.rows = [mock_row]
        
        mock_doc = Mock()
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_doc.tables = [mock_table]
        
        mock_docx.return_value = mock_doc
        
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            f.write(b'fake docx content')
            temp_path = f.name
        
        try:
            result = self.preprocessor.process_docx(temp_path)
            
            assert isinstance(result, ProcessedDocument)
            assert result.format == DocumentFormat.DOCX
            assert "First paragraph" in result.text_content
            assert "Second paragraph" in result.text_content
            assert "Cell 1 | Cell 2" in result.text_content
            assert result.metadata['paragraph_count'] == 2
            assert result.metadata['table_count'] == 1
            assert result.metadata['has_tables'] is True
            
        finally:
            os.unlink(temp_path)
    
    @patch('src.document.preprocessing.openpyxl.load_workbook')
    def test_process_xlsx(self, mock_load_workbook):
        """Test XLSX processing."""
        # Mock worksheet
        mock_sheet = Mock()
        mock_sheet.iter_rows.return_value = [
            ('Header 1', 'Header 2', 'Header 3'),
            ('Value 1', 'Value 2', 'Value 3'),
            (None, 'Value 4', None)
        ]
        
        # Mock workbook
        mock_workbook = Mock()
        mock_workbook.sheetnames = ['Sheet1']
        mock_workbook.__getitem__ = Mock(return_value=mock_sheet)
        
        mock_load_workbook.return_value = mock_workbook
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(b'fake xlsx content')
            temp_path = f.name
        
        try:
            result = self.preprocessor.process_xlsx(temp_path)
            
            assert isinstance(result, ProcessedDocument)
            assert result.format == DocumentFormat.XLSX
            assert "Header 1 | Header 2 | Header 3" in result.text_content
            assert "Value 1 | Value 2 | Value 3" in result.text_content
            assert result.metadata['sheet_count'] == 1
            assert 'Sheet1' in result.metadata['sheet_names']
            
        finally:
            os.unlink(temp_path)
    
    @patch.object(DocumentPreprocessor, 'download_file')
    @patch.object(DocumentPreprocessor, 'process_text')
    def test_process_document_success(self, mock_process_text, mock_download):
        """Test successful document processing from URL."""
        # Mock download
        temp_path = "/tmp/test.txt"
        mock_download.return_value = (temp_path, "text/plain")
        
        # Mock processing
        expected_result = ProcessedDocument(
            format=DocumentFormat.TEXT,
            text_content="Test content",
            original_filename="test.txt",
            file_size=100
        )
        mock_process_text.return_value = expected_result
        
        file_url = "https://example.com/test.txt"
        result = self.preprocessor.process_document(file_url)
        
        assert result == expected_result
        mock_download.assert_called_once_with(file_url)
        mock_process_text.assert_called_once_with(temp_path)
    
    @patch.object(DocumentPreprocessor, 'download_file')
    def test_process_document_unknown_format_fallback(self, mock_download):
        """Test processing unknown format with fallback."""
        temp_path = "/tmp/test.unknown"
        mock_download.return_value = (temp_path, "application/octet-stream")
        
        with patch.object(self.preprocessor, 'process_text') as mock_text, \
             patch.object(self.preprocessor, 'process_image') as mock_image, \
             patch('os.path.exists', return_value=True), \
             patch('os.unlink'):
            
            # First fallback (text) fails
            mock_text.side_effect = Exception("Not text")
            
            # Second fallback (image) succeeds
            expected_result = ProcessedDocument(
                format=DocumentFormat.IMAGE,
                text_content="",
                original_filename="test.unknown",
                file_size=100
            )
            mock_image.return_value = expected_result
            
            file_url = "https://example.com/test.unknown"
            result = self.preprocessor.process_document(file_url)
            
            assert result == expected_result
            mock_text.assert_called_once()
            mock_image.assert_called_once()


class TestProcessedDocument:
    """Test cases for ProcessedDocument."""
    
    def test_has_text_content(self):
        """Test text content detection."""
        doc_with_text = ProcessedDocument(
            format=DocumentFormat.TEXT,
            text_content="Some content"
        )
        assert doc_with_text.has_text_content() is True
        
        doc_without_text = ProcessedDocument(
            format=DocumentFormat.IMAGE,
            text_content=""
        )
        assert doc_without_text.has_text_content() is False
        
        doc_whitespace_only = ProcessedDocument(
            format=DocumentFormat.TEXT,
            text_content="   \n\t  "
        )
        assert doc_whitespace_only.has_text_content() is False
    
    def test_has_images(self):
        """Test image content detection."""
        doc_with_images = ProcessedDocument(
            format=DocumentFormat.PDF,
            image_paths=["/path/to/image1.png", "/path/to/image2.png"]
        )
        assert doc_with_images.has_images() is True
        
        doc_without_images = ProcessedDocument(
            format=DocumentFormat.TEXT,
            image_paths=[]
        )
        assert doc_without_images.has_images() is False
    
    def test_get_content_summary(self):
        """Test content summary generation."""
        doc = ProcessedDocument(
            format=DocumentFormat.PDF,
            text_content="Test content",
            image_paths=["/path/to/image.png"],
            metadata={"page_count": 2},
            original_filename="test.pdf",
            file_size=1024
        )
        
        summary = doc.get_content_summary()
        
        assert summary['format'] == 'pdf'
        assert summary['has_text'] is True
        assert summary['text_length'] == len("Test content")
        assert summary['image_count'] == 1
        assert summary['metadata'] == {"page_count": 2}
        assert summary['original_filename'] == "test.pdf"
        assert summary['file_size'] == 1024


if __name__ == '__main__':
    pytest.main([__file__])