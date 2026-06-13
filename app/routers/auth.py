import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app import models, schemas, utils, database
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
import os
import uuid
from app.routers.auth2 import get_current_user

router = APIRouter(tags=["Authentication"])


def send_verification_email(receiver_email: str, code: str):
   
    sender_email = os.environ.get('EMAIL_USER')
    sender_pass = os.environ.get('EMAIL_PASS')
    
    if not sender_email or not sender_pass:
        print("تحذير: بيانات الإيميل غير موجودة في متغيرات البيئة")
        return

    msg = MIMEText(f"مرحباً بك في منصة DrawSense!\n\nكود التأكيد الخاص بك هو: {code}\n\nيرجى إدخال هذا الكود لتفعيل حسابك.")
    msg['Subject'] = 'كود تفعيل حسابك في DrawSense'
    msg['From'] = f"DrawSense <{sender_email}>"
    msg['To'] = receiver_email

    try:
    
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"✅ تم إرسال كود التفعيل بنجاح إلى: {receiver_email}")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء إرسال الإيميل: {e}")


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    # المستخدم موجود؟
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # كود تأكيد عشوائي، توقيت الجهاز
    v_code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.now() + timedelta(minutes=5)


    hashed_pwd = utils.hash(user.password)

    # مستخدم جديد
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_pwd,
        full_name=user.full_name,
        is_active=False,
        verification_code=v_code,
        verification_expires_at=expires_at
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

 
    send_verification_email(user.email, v_code)

    return {"message": "تم التسجيل بنجاح، يرجى إدخال كود التحقق المرسل إلى إيميلك"}


@router.post("/verify-code")
def verify_code(payload: schemas.VerifyCodeRequest, db: Session = Depends(database.get_db)):
    # المستخدم موجود؟
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not Found")

    # حسابه مفعل؟
    if user.is_active:
        return {"message": "Account is already activated"}

    # الكود
    if user.verification_code != payload.code:
        raise HTTPException(status_code=400, detail="Verification code is incorrect")
        
    if datetime.now() > user.verification_expires_at:
        raise HTTPException(status_code=400, detail="Verification code is expired. Try Again")

    # تفعيل الحساب
    user.is_active = True
    user.verification_code = None
    user.verification_expires_at = None
    
    db.commit()

    return {"message": "Your account was succesfully created"}


@router.post("/login", response_model=schemas.Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please activate your account via email first"
        )

    if not utils.verify(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = utils.create_access_token(data={"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password")
def forgot_password(email: str, db: Session = Depends(database.get_db)):
    # الحساب موجود؟
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found.")

    # كود تأكيد
    reset_code = f"{random.randint(100000, 999999)}"
    user.verification_code = reset_code
    user.verification_expires_at = datetime.now() + timedelta(minutes=5)
    
    db.commit()

    sender_email = os.environ.get('EMAIL_USER')
    sender_pass = os.environ.get('EMAIL_PASS')
    
    if sender_email and sender_pass:
        msg = MIMEText(f"طلب استعادة كلمة المرور في منصة DrawSense.\n\nكود الاستعادة الخاص بك هو: {reset_code}\n\n(هذا الكود صالح لمدة 5 دقائق)")
        msg['Subject'] = 'استعادة كلمة المرور - DrawSense'
        msg['From'] = f"DrawSense <{sender_email}>"
        msg['To'] = email

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, email, msg.as_string())
            server.quit()
            print(f"✅ تم إرسال كود الاستعادة بنجاح إلى: {email}")
        except Exception as e:
            print(f"❌ حدث خطأ أثناء إرسال كود الاستعادة: {e}")

    return {"message": "Reset code has been generated and sent."}

@router.post("/reset-password")
def reset_password(payload: schemas.VerifyCodeRequest, db: Session = Depends(database.get_db)):
    pass


@router.put("/profile", response_model=schemas.UserResponse)
def update_profile(
    update_data: schemas.UpdateProfileRequest, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(get_current_user)
):
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name
    
    if update_data.bio is not None:
        current_user.bio = update_data.bio
        
    if update_data.email_notifications is not None:
        current_user.email_notifications = update_data.email_notifications
        
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/change-password")
def change_password(
    passwords: schemas.ChangePasswordRequest, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(get_current_user)
):
   
    if not utils.verify(passwords.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect Password")
        
    current_user.hashed_password = utils.hash(passwords.new_password)
    db.commit()
    return {"message": "Password is updated succesfully"}

@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...), 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(get_current_user)
):
 
    upload_dir = "assets/avatars"
    os.makedirs(upload_dir, exist_ok=True)
    

    file_extension = file.filename.split(".")[-1]
    file_name = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(upload_dir, file_name)
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
  
    current_user.profile_image = file_path
    db.commit()
    
    return {"message": "رفعت الصورة", "profile_image": file_path}

@router.delete("/remove-avatar")
def remove_avatar(
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(get_current_user)
):
    current_user.profile_image = None
    db.commit()
    return {"message": "أزيلت الصورة"}