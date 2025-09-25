import os
import shutil
import hashlib
import mimetypes
from pathlib import Path
from typing import BinaryIO, Optional
from uuid import uuid4
from datetime import datetime
from .models import Document, DocumentType
from .config import get_config

class DocumentManager:
    """Manages document storage and retrieval"""
    
    def __init__(self):
        config = get_config()
        self.documents_dir = Path(config.storage.documents_dir)
        self.max_file_size_bytes = config.storage.max_file_size_mb * 1024 * 1024
        self.documents_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_document_type(self, mime_type: str) -> DocumentType:
        """Determine document type from MIME type"""
        if mime_type.startswith('image/'):
            return DocumentType.IMAGE
        elif mime_type == 'application/pdf':
            return DocumentType.PDF
        elif mime_type.startswith('text/'):
            return DocumentType.TEXT
        elif mime_type in ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            return DocumentType.SPREADSHEET
        elif mime_type in ['application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation']:
            return DocumentType.PRESENTATION
        else:
            return DocumentType.OTHER
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def store_document(self, file_obj: BinaryIO, original_filename: str, metadata: Optional[dict] = None) -> Document:
        """Store a document and return its metadata"""
        # Generate unique ID and file path
        doc_id = str(uuid4())
        file_extension = Path(original_filename).suffix
        stored_filename = f"{doc_id}{file_extension}"
        file_path = self.documents_dir / stored_filename
        
        # Check file size
        file_obj.seek(0, 2)  # Seek to end
        file_size = file_obj.tell()
        file_obj.seek(0)  # Reset to beginning
        
        if file_size > self.max_file_size_bytes:
            raise ValueError(f"File size exceeds maximum allowed size of {self.max_file_size_mb}MB")
        
        # Save file
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(file_obj, f)
        
        # Determine MIME type and document type
        mime_type, _ = mimetypes.guess_type(original_filename)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        document_type = self._get_document_type(mime_type)
        
        # Calculate checksum
        checksum = self._calculate_checksum(file_path)
        
        # Create document metadata
        document = Document(
            id=doc_id,
            title=original_filename,
            file_path=str(file_path),
            document_type=document_type,
            mime_type=mime_type,
            size_bytes=file_size,
            checksum=checksum,
            metadata=metadata or {}
        )
        
        return document
    
    def get_document_path(self, document: Document) -> Path:
        """Get the file path for a document"""
        return Path(document.file_path)
    
    def delete_document_file(self, document: Document) -> bool:
        """Delete the physical file for a document"""
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def update_document_file(self, document: Document, file_obj: BinaryIO) -> Document:
        """Update the physical file for a document"""
        file_path = Path(document.file_path)
        
        # Check file size
        file_obj.seek(0, 2)
        file_size = file_obj.tell()
        file_obj.seek(0)
        
        if file_size > self.max_file_size_bytes:
            raise ValueError(f"File size exceeds maximum allowed size of {self.max_file_size_mb}MB")
        
        # Save new file
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(file_obj, f)
        
        # Update document metadata
        document.size_bytes = file_size
        document.checksum = self._calculate_checksum(file_path)
        document.updated_at = datetime.now()
        
        return document
