Infrastructure Deployment

Make sure you have Terraform installed.

```bash
cd infrastructure/
terraform init
terraform apply
````

This will:

* Create a VPC with a public subnet
* Launch an EC2 instance to host the API
* Provision an S3 bucket for model storage
* Deploy a Lambda function for sending alerts

---

## 🧠 Train ML Models

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Train models:

```bash
python train_models.py
```

This script will train and save:

* `earthquake_lstm.h5`: LSTM model for earthquake prediction
* `flood_rf.pkl`: Random Forest model for flood prediction

Artifacts are logged via MLflow and saved in the `models/` directory.

---

## ⚙️ CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/deploy.yml`) automates:

1. Code testing using `pytest`
2. Building and pushing the Docker image to Amazon ECR
3. Deploying the updated image to the EC2 instance via SSH

This workflow runs on every push or PR to the `main` branch.

Secrets needed in GitHub:

* `AWS_ACCESS_KEY_ID`
* `AWS_SECRET_ACCESS_KEY`
* `EC2_HOST`
* `EC2_SSH_KEY` (your private key)

---

## 🔐 Environment Variables (Lambda)

Ensure the following variables are set for your Lambda function (used for sending alerts):

* `TWILIO_SID`
* `TWILIO_TOKEN`

---

## 📬 Future Improvements

* Integrate API Gateway for serverless endpoints
* Add CloudWatch logging and monitoring
* Improve data pipeline with real-time ingestion (Kafka, AWS Kinesis)
* UI dashboard for monitoring predictions and alerts

