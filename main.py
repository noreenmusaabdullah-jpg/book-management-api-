import secrets
from datetime import date
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./books.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class BookModel(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    author = Column(String, nullable=False)
    publishedDate = Column(Date, nullable=False)
    numberOfPages = Column(Integer, nullable=False)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Validation Schemas
class BookBase(BaseModel):
    title: str
    author: str
    publishedDate: date
    numberOfPages: int

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    publishedDate: Optional[date] = None
    numberOfPages: Optional[int] = None

class BookResponse(BookBase):
    id: int
    class Config:
        from_attributes = True

# Security Settings
security = HTTPBasic()
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password123"

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Endpoints API Mesh
app = FastAPI(title="Book Management API", version="1.0.0")

@app.post("/api/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(book: BookCreate, db: Session = Depends(get_db), username: str = Depends(verify_credentials)):
    db_book = BookModel(**book.model_dump())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@app.get("/api/books", response_model=List[BookResponse])
def get_all_books(db: Session = Depends(get_db)):
    return db.query(BookModel).all()

@app.get("/api/books/{book_id}", response_model=BookResponse)
def get_book_details(book_id: int, db: Session = Depends(get_db)):
    db_book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book

@app.put("/api/books/{book_id}", response_model=BookResponse)
def update_book(book_id: int, book_update: BookUpdate, db: Session = Depends(get_db), username: str = Depends(verify_credentials)):
    db_book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    for key, value in book_update.model_dump(exclude_unset=True).items():
        setattr(db_book, key, value)
    db.commit()
    db.refresh(db_book)
    return db_book

@app.delete("/api/books/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db), username: str = Depends(verify_credentials)):
    db_book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if not db_book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(db_book)
    db.commit()
    return {"message": "Book successfully deleted"}
