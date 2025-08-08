
# Invoice Extraction

Invoice Extraction is a project designed to extract structured data from invoice files like invoice.pdf. The extracted information is automatically converted into CSV and JSON formats for easy data handling, analysis, or integration into other systems.





## Clone

To clone this project 

```bash
git clone https://github.com/Tathagat-K/InvoiceStructure.git

# Navigate to the project directory
cd [repository-name]
```

## Environment 
After cloning, run this command:

```bash
python -m venv your_env_name
```

To activate your_env_name, run this command:
```bash
your_env_name/scripts/activate
```

## Alembic Commands
After your_env_name is installed and set up, run the following Alembic commands:

```bash
alembic init alembic
alembic revision --autogenerate -m "message"
alembic upgrade head
```
## Database url
```bash
postgresql+asyncpg://db_username:db_password@db_host_name:db_port/your_db_projectname
```

## Environment Variables
Create a .env file in the root directory with the following values:

```bash
DATABASE_USERNAME=your_db_user
DATABASE_PASSWORD=your_db_password
DATABASE_HOSTNAME=localhost
DATABASE_PORT=your_db_port
DATABASE_NAME=your_db_name
GOOGLE_API_KEY=your_api_key
```

## To Run Project
```bash
uvicorn app.main:app --reload --port your_port
```