# infrastructure/main.tf

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_vpc" "disaster_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "DisasterPredictionVPC"
  }
}

resource "aws_subnet" "public_subnet" {
  vpc_id            = aws_vpc.disaster_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"

  tags = {
    Name = "PublicSubnet"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.disaster_vpc.id

  tags = {
    Name = "DisasterPredictionIGW"
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.disaster_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "PublicRouteTable"
  }
}

resource "aws_route_table_association" "public_rta" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_security_group" "api_sg" {
  name        = "api_security_group"
  description = "Allow API traffic"
  vpc_id      = aws_vpc.disaster_vpc.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "api_server" {
  ami             = "ami-0c55b159cbfafe1f0" # Ubuntu 20.04 LTS
  instance_type   = "t3.large"
  subnet_id       = aws_subnet.public_subnet.id
  security_groups = [aws_security_group.api_sg.name]
  key_name        = "disaster-key"

  user_data = <<-EOF
              #!/bin/bash
              apt-get update
              apt-get install -y docker.io
              systemctl start docker
              systemctl enable docker
              docker run -d -p 8000:8000 --name disaster-api disaster-prediction-api:latest
              EOF

  tags = {
    Name = "DisasterPredictionAPI"
  }
}

resource "aws_s3_bucket" "model_bucket" {
  bucket = "disaster-prediction-models"
  acl    = "private"

  tags = {
    Name = "ModelStorage"
  }
}

resource "aws_iam_role" "lambda_role" {
  name = "lambda_execution_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_lambda_function" "alert_function" {
  function_name = "send-disaster-alerts"
  handler       = "index.handler"
  runtime       = "python3.8"
  role          = aws_iam_role.lambda_role.arn
  s3_bucket     = "disaster-alert-lambda"
  s3_key        = "lambda.zip"

  environment {
    variables = {
      TWILIO_SID   = var.twilio_sid
      TWILIO_TOKEN = var.twilio_token
    }
  }
}
