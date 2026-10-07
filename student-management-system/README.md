# Student Management System

Flask + SQLite + Chart.js. CRUD, search, filter and a live analytics dashboard.

## Run locally (Ubuntu)
```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip
cd student-management-system
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py            # http://localhost:5000
```
`students.db` is created automatically and seeded with sample students on first run.

## Deploy on AWS EC2 or Azure VM (Ubuntu)
1. Open inbound port **5000** (or 80 if using nginx):
   - AWS: EC2 > Security Group > Inbound rules > Custom TCP 5000, source 0.0.0.0/0
   - Azure: VM > Networking > Add inbound port rule > port 5000
2. Copy the folder to the VM: `scp -i key.pem -r student-management-system ubuntu@<PUBLIC-IP>:~`
3. SSH in and run the "Run locally" steps above, then start with gunicorn:
   ```bash
   gunicorn -w 2 -b 0.0.0.0:5000 app:app
   ```
4. Browse to `http://<PUBLIC-IP>:5000`

### Keep it running (systemd)
```bash
sudo tee /etc/systemd/system/students.service <<UNIT
[Unit]
Description=Student Management System
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/student-management-system
ExecStart=/home/ubuntu/student-management-system/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload && sudo systemctl enable --now students
```
(On Azure the default user is the one you chose at VM creation, e.g. `azureuser`; adjust `User` and paths.)

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/students?q=&department=` | List / search |
| POST | `/api/students` | Create |
| PUT | `/api/students/<id>` | Update |
| DELETE | `/api/students/<id>` | Delete |
| GET | `/api/stats` | Dashboard data |
| GET | `/health` | Health check |
