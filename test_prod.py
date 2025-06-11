import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app, SQLALCHEMY_DATABASE_URL, get_db
from app.models import Base, User
from app.schemas import UserCreate
from app.utils import hash_password

@pytest.fixture(scope='module')
def test_client():
    """Создает клиент для тестирования"""
    client = TestClient(app)
    return client

@pytest.fixture(scope='session', autouse=True)
def setup_database():
    """Подготавливаем базу данных для тестов"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield TestingSessionLocal()

@pytest.fixture(scope='function')
def mock_session(setup_database):
    """Получаем сессию БД для одного теста"""
    session = setup_database
    yield session
    session.rollback()

def test_register_user(test_client, mock_session):
    """
    Тест регистрации нового пользователя
    """
    new_user = UserCreate(username="testuser", email="test@example.com", password="secret")
    response = test_client.post("/register/", json=new_user.model_dump())
    assert response.status_code == 200
    created_user = response.json()
    assert created_user['email'] == "test@example.com"

def test_login_user(test_client, mock_session):
    """
    Тест авторизации пользователя
    """
    # Регистрация нового пользователя
    new_user = UserCreate(username="login_test", email="login@test.com", password="password")
    test_client.post("/register/", json=new_user.model_dump())
    
    # Попытка входа
    response = test_client.post("/token", data={
        "username": "login_test",
        "password": "password"
    })
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens

def test_get_current_user(test_client, mock_session):
    """
    Тест получения текущего активного пользователя
    """
    # Сначала регистрируем пользователя
    new_user = UserCreate(username="current_user", email="current@user.com", password="passwd")
    test_client.post("/register/", json=new_user.model_dump())
    
    # Получаем токен
    response = test_client.post("/token", data={
        "username": "current_user",
        "password": "passwd"
    })
    token = response.json()['access_token']
    
    # Пробуем получить информацию о себе
    headers = {'Authorization': f'Bearer {token}'}
    response = test_client.get("/users/me", headers=headers)
    assert response.status_code == 200
    retrieved_user = response.json()
    assert retrieved_user['username'] == "current_user"

def test_read_all_users(test_client, mock_session):
    """
    Тест чтения списка всех пользователей
    """
    # Зарегистрируем двух пользователей
    user1 = UserCreate(username="user1", email="user1@email.com", password="pw1")
    user2 = UserCreate(username="user2", email="user2@email.com", password="pw2")
    test_client.post("/register/", json=user1.model_dump())
    test_client.post("/register/", json=user2.model_dump())
    
    # Читаем список пользователей
    response = test_client.get("/users/")
    assert response.status_code == 200
    users_list = response.json()
    assert len(users_list) >= 2

def test_update_user(test_client, mock_session):
    """
    Тест обновления профиля пользователя
    """
    # Регистрируем пользователя
    new_user = UserCreate(username="update_user", email="update@user.com", password="pwd")
    test_client.post("/register/", json=new_user.model_dump())
    
    # Обновляем профиль
    updated_user = {"full_name": "Updated Name"}
    response = test_client.put(f"/users/{new_user.id}", json=updated_user)
    assert response.status_code == 200
    updated_profile = response.json()
    assert updated_profile['full_name'] == "Updated Name"

def test_delete_user(test_client, mock_session):
    """
    Тест удаления пользователя
    """
    # Регистрируем пользователя
    new_user = UserCreate(username="delete_user", email="del@user.com", password="pwd")
    response = test_client.post("/register/", json=new_user.model_dump())
    user_id = response.json()['id']
    
    # Удаляем пользователя
    response = test_client.delete(f"/users/{user_id}")
    assert response.status_code == 200
    deleted_user = response.json()
    assert deleted_user['id'] == user_id
