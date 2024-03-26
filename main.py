from fastapi import FastAPI, HTTPException, BackgroundTasks, status, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from database import SessionLocal, engine
from schemas import BookCreate, Book, ReviewCreate, Review
import models

app = FastAPI()

# Database CRUD operations

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_book(db: Session, book: BookCreate) -> Book:
    db_book = models.Book(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

def create_review(db: Session, review: ReviewCreate, book_id: int) -> Review:
    db_review = models.Review(**review.dict(), book_id=book_id)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

def get_books(db: Session, author: Optional[str] = None, publication_year: Optional[int] = None) -> List[Book]:
    query = db.query(models.Book)
    if author:
        query = query.filter(models.Book.author == author)
    if publication_year:
        query = query.filter(models.Book.publication_year == publication_year)
    return query.all()

def get_reviews(db: Session, book_id: int) -> List[Review]:
    return db.query(models.Review).filter(models.Review.book_id == book_id).all()

def get_book(db: Session, book_id: int) -> Book:
    return db.query(models.Book).filter(models.Book.id == book_id).first()

def delete_book(db: Session, book_id: int) -> dict:
    db_book = get_book(db, book_id)
    if not db_book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    db.delete(db_book)
    db.commit()
    return {"message": "Book deleted successfully"}

def update_book(db: Session, book_id: int, book: BookCreate) -> Book:
    db_book = get_book(db, book_id)
    if not db_book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    for key, value in book.dict().items():
        setattr(db_book, key, value)
    db.commit()
    db.refresh(db_book)
    return db_book

def delete_review(db: Session, review_id: int) -> dict:
    db_review = db.query(models.Review).filter(models.Review.id == review_id).first()
    if not db_review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    db.delete(db_review)
    db.commit()
    return {"message": "Review deleted successfully"}

# Endpoints

@app.post("/books/", response_model=Book)
def add_book(book: BookCreate, db: Session = Depends(get_db)) -> Book:
    return create_book(db, book)

@app.post("/books/{book_id}/reviews/", response_model=Review)
def submit_review(book_id: int, review: ReviewCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Review:
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    
    review_obj = create_review(db, review, book_id)
    background_tasks.add_task(send_confirmation_email, review_obj.text)  # Background task for sending email
    return review_obj

@app.get("/books/", response_model=List[Book])
def get_books_list(author: Optional[str] = None, publication_year: Optional[int] = None, db: Session = Depends(get_db)) -> List[Book]:
    return get_books(db, author, publication_year)

@app.post("/books/", response_model=Book)
def add_book(book: BookCreate, db: Session = Depends(get_db)) -> Book:
    new_book = create_book(db, book)
    return new_book  # The book object returned here will contain the ID

@app.get("/books/{book_id}/reviews/", response_model=List[Review])
def get_book_reviews(book_id: int, db: Session = Depends(get_db)) -> List[Review]:
    book = get_book(db, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    
    return get_reviews(db, book_id)

@app.put("/books/{book_id}/", response_model=Book)
def update_book_details(book_id: int, book: BookCreate, db: Session = Depends(get_db)) -> Book:
    return update_book(db, book_id, book)

@app.delete("/books/{book_id}/", response_model=dict)
def delete_book_endpoint(book_id: int, db: Session = Depends(get_db)) -> dict:
    return delete_book(db, book_id)

@app.delete("/reviews/{review_id}/", response_model=dict)
def delete_review_endpoint(review_id: int, db: Session = Depends(get_db)) -> dict:
    return delete_review(db, review_id)

# Background task
def send_confirmation_email(review_text: str) -> None:
    # Simulated email sending task
    print(f"Sending confirmation email for review: {review_text}")
