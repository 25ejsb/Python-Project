to run on a domain, do $ngrok http 5000, but run $python main.py first

use fly.io
do $fly postgres create
connect those to sqlite like this "postgresql://user:passwd@hostname:5432"
$fly deploy

aws
ssh -i pydocs-key.pem ec2-user@18.226.187.164
do python3 -m venv venv
then source venv/bin/activate
cd pydocs
pip install -r requirements.txt
run python3 app.py
do gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:8080 app:app --daemon to keep app running without just the terminal
http://18.226.187.164:8080/
check http