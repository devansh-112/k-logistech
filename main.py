from app import app
import routes

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
