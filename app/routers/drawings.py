import uuid
import os
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas, database
from app.routers.auth2 import get_current_user


router = APIRouter(tags=["Drawings Analysis"])

UPLOAD_DIR = "assets/drawings"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

def validate_extension(filename: str):
    ext = filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"نوع الملف غير مدعوم. المسموح به: {ALLOWED_EXTENSIONS}"
        )
    return ext



@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=schemas.DrawingResponse)
async def upload_and_analyze(
        title: str = Form("Child's Drawing'"),  
        is_favorite: bool = Form(False),
        file: UploadFile = File(...),
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user)
):

    # المودل جاهز؟
  #  if model_container.get("model") is None:
   #     raise HTTPException(
    #        status_code=503,
    #        detail="محرك التحليل الذكي غير جاهز حاليًا، يرجى المحاولة لاحقًا"
    #    )

    # لازم صورة
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="يجب رفع ملف صورة فقط")

    file_extension = validate_extension(file.filename)
   
    #  حفظ الملف على السيرفر
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        contents = await file.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="حجم الصورة كبير جدًا (الحد الأقصى 5MB)")

        with open(file_path, "wb") as buffer:
            buffer.write(contents)
    except Exception:
        raise HTTPException(status_code=500, detail="فشل في حفظ الصورة على السيرفر")

    #  تحليل الـ AI
  #  try:
   #     ai_results = await run_ai_analysis(file_path)
  #  except Exception as e:
       # if os.path.exists(file_path):
       #     os.remove(file_path)
     #   raise HTTPException(status_code=500, detail=f"فشل تحليل الـ AI: {str(e)}")

    # الحفظ في الداتابيز
    drawing_data = {
        "user_id": current_user.id,
        "image_url": file_path.replace("\\", "/"),
        "is_favorite": is_favorite
    }
    
    # الحقل موجود؟
    if hasattr(models.Drawing, 'title'):
        drawing_data["title"] = title

    new_drawing = models.Drawing(**drawing_data)
    db.add(new_drawing)
    db.commit()
    db.refresh(new_drawing)
   
    return {
        "id": new_drawing.id,
        "user_id": new_drawing.user_id,
        "image_url": new_drawing.image_url,
        "created_at": new_drawing.uploaded_at,  
        "title": title,
        "is_favorite": new_drawing.is_favorite,
        "analysis_output": None
    }

@router.get("/my-drawings", response_model=List[schemas.DrawingResponse])
def get_my_drawings(
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user),
        skip: int = 0,
        limit: int = 10
):
    drawings = db.query(models.Drawing) \
        .filter(models.Drawing.user_id == current_user.id) \
        .order_by(models.Drawing.id.desc()) \
        .offset(skip) \
        .limit(limit) \
        .all()
    
  
    result_list = []
    for d in drawings:
        result_list.append({
            "id": d.id,
            "user_id": d.user_id,
            "image_url": d.image_url,
            "created_at": d.uploaded_at,
            "title": getattr(d, 'title', None) or "رسمة طفل",
            "is_favorite": getattr(d, 'is_favorite', False),
            "analysis_output": None
        })
        
    return result_list

@router.delete("/{drawing_id}", status_code=status.HTTP_200_OK)
def delete_drawing(
        drawing_id: int,
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user)
):
    drawing = db.query(models.Drawing).filter(
        models.Drawing.id == drawing_id,
        models.Drawing.user_id == current_user.id
    ).first()

    if not drawing:
        raise HTTPException(status_code=404, detail="الرسمة غير موجودة")

    if os.path.exists(drawing.image_url):
        os.remove(drawing.image_url)

    db.delete(drawing)
    db.commit()
    return {"message": "حُذِفت الرسمة بنجاح"}




@router.get("/favorites", response_model=List[schemas.DrawingResponse])
def get_favorite_drawings(
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user),
        skip: int = 0,
        limit: int = 10
):
    
    drawings = db.query(models.Drawing) \
        .filter(models.Drawing.user_id == current_user.id, models.Drawing.is_favorite == True) \
        .order_by(models.Drawing.id.desc()) \
        .offset(skip) \
        .limit(limit) \
        .all()
    
    result_list = []
    for d in drawings:
        result_list.append({
            "id": d.id,
            "user_id": d.user_id,
            "image_url": d.image_url,
            "created_at": d.uploaded_at,
            "title": getattr(d, 'title', None) or "رسمة طفل",
            "is_favorite": d.is_favorite,
            "analysis_output": None
        })
        
    return result_list


@router.patch("/{drawing_id}/toggle-favorite")
def toggle_drawing_favorite(
        drawing_id: int,
        db: Session = Depends(database.get_db),
        current_user: models.User = Depends(get_current_user)
):
    
    drawing = db.query(models.Drawing).filter(
        models.Drawing.id == drawing_id,
        models.Drawing.user_id == current_user.id
    ).first()

    if not drawing:
        raise HTTPException(status_code=404, detail="الرسمة غير موجودة")

  
    drawing.is_favorite = not drawing.is_favorite
    db.commit()
    db.refresh(drawing)

    status_str = "إضافتها إلى" if drawing.is_favorite else "إزالتها من"
    return {
        "message": f"تم {status_str} المفضلة بنجاح",
        "drawing_id": drawing.id,
        "is_favorite": drawing.is_favorite
    }