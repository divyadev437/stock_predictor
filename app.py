from project import create_app
from project.extensions import db # Import db

app = create_app()

# --- Add this command function ---
@app.cli.command("init-db")
def init_db():
    
    print("Creating database tables...")
    with app.app_context(): # Ensure we're in the app context
        
        db.create_all()
    print("Database tables created.")
# ---------------------------------

if __name__ == '__main__':
    app.run(debug=True)