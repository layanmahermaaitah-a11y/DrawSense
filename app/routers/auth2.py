from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app import database, models, utils

# التأكد من أن الرابط يطابق الـ Prefix الموجود في main.py
# إذا كان في main: app.include_router(auth.router, prefix="/auth")
# فيجب أن يكون هنا: "auth/login"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please login again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # فك تشفير الـ JWT
        payload = jwt.decode(token, utils.SECRET_KEY, algorithms=[utils.ALGORITHM])

        # التعديل الجوهري: البحث عن user_id وليس sub
        user_id: int = payload.get("user_id")

        if user_id is None:
            raise credentials_exception

        # إذا كان schema.TokenData يتوقع email، يمكننا تغييره لـ id أو تركه مؤقتاً
        # لكن الأهم هو البحث في قاعدة البيانات باستخدام الـ ID
    except JWTError:
        raise credentials_exception

    # جلب المستخدم من PostgresSQL باستخدام الـ ID لأنه أسرع وأدق
    user = db.query(models.User).filter(models.User.id == user_id).first()

    if user is None:
        raise credentials_exception

    return user