from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "DevOps Deployment Automation Platform is running!"

@app.route("/health")
def health():
    return jsonify(status="UP")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
