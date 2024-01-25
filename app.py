from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session, send_file
from flask_socketio import SocketIO, emit, join_room, leave_room, send
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_wtf import FlaskForm
from flask_wtf.form import _Auto
from wtforms import StringField, SubmitField, PasswordField, EmailField, TextAreaField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
import os
file_path = os.path.abspath(os.getcwd())+"/database.db"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+file_path
db = SQLAlchemy(app)
login_manager = LoginManager(app)
Bootstrap(app)
socketio = SocketIO(app, debug=True)
import smtplib, json
# os.environ['PATH'] = "C:\Program Files\GTK3-Runtime Win64\bin" + os.pathsep + os.environ.get('PATH', '')

from weasyprint import HTML
from io import BytesIO

class LoginForm(FlaskForm):
    username = StringField("Enter Your Username:", validators=[DataRequired()])
    password = PasswordField("Enter Your Password:", validators=[DataRequired()])
    submit = SubmitField("Log Me In!")

class RegisterForm(FlaskForm):
    username = StringField("Enter A Username:", validators=[DataRequired()])
    password = PasswordField("Enter A Password", validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")

class DocumentForm(FlaskForm):
    name = StringField("Enter A Document Name:", validators=[DataRequired()])
    submit = SubmitField("Create")

class ShareForm(FlaskForm):
    username = StringField("Enter A Username:", validators=[DataRequired()])
    submit = SubmitField("Share")

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(1000))
    password = db.Column(db.String(1000))
    documents = relationship("Document", back_populates="creator")
    user_shares = relationship("Share", back_populates="share_author")
    user_suggestions = relationship("Suggestion", back_populates="suggestion_author")
    user_server = relationship("ServerUser", back_populates="user_author")
    user_messages = relationship("ChatMessage", back_populates="message_author")
    user_edits = relationship("EditRequest", back_populates="creator")
    def __init__(self, username, password):
        self.username = username
        self.password = password
    def __repr__(self):
        return f"<User {self.username}>"
    
class Document(db.Model):
    __tablename__ = "documents"
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, ForeignKey("users.id"))
    name = db.Column(db.String(1000))
    content = db.Column(db.Text)
    creator = relationship("User", back_populates="documents")
    shares = relationship("Share", back_populates="parent_doc")
    suggestions = relationship("Suggestion", back_populates="parent_doc")
    server_users = relationship("ServerUser", back_populates="parent_doc")
    messages = relationship("ChatMessage", back_populates="parent_doc")
    document_edits = relationship("EditRequest", back_populates="editdoc")
    default_role = db.Column(db.String(1000))
    privacy = db.Column(db.String(1000))
    views = db.Column(db.Integer)
    def __init__(self, name, creator_id, content, default_role, privacy, views):
        self.name = name
        self.creator_id = creator_id
        self.content = content
        self.default_role = default_role
        self.privacy = privacy
        self.views = views
    def __repr__(self):
        return f"<Document {self.name}>"
    
class ServerUser(db.Model):
    __tablename__ = "serverusers"
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, ForeignKey("documents.id"))
    author = db.Column(db.Integer, ForeignKey("users.id"))
    user_author = relationship("User", back_populates="user_server")
    parent_doc = relationship("Document", back_populates="server_users")
    username = db.Column(db.String(1000))
    socket_id = db.Column(db.String(1000))
    def __init__(self, username, user_author, parent_doc, socket_id):
        self.username = username
        self.user_author = user_author
        self.parent_doc = parent_doc
        self.socket_id = socket_id
    def __repr__(self):
        return f"<ServerUser {self.username}>"
    
class Share(db.Model):
    __tablename__ = "share"
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, ForeignKey("documents.id"))
    author = db.Column(db.Integer, ForeignKey("users.id"))
    share_author = relationship("User", back_populates="user_shares")
    parent_doc = relationship("Document", back_populates="shares")
    username = db.Column(db.String(1000))
    role = db.Column(db.String(1000))
    def __init__(self, username, share_author, parent_doc, role):
        self.username = username
        self.share_author = share_author
        self.parent_doc = parent_doc
        self.role = role
    def __repr__(self):
        return f"<Share {self.parent_doc} for {self.username}>"
    
class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, ForeignKey("documents.id"))
    author = db.Column(db.Integer, ForeignKey("users.id"))
    suggestion_author = relationship("User", back_populates="user_suggestions")
    parent_doc = relationship("Document", back_populates="suggestions")
    suggestion_highlight = db.Column(db.String(100000))
    suggestion_text = db.Column(db.String(100000))
    done = db.Column(db.Boolean, default=False, nullable=False)
    def __init__(self, suggestion_highlight, suggestion_text, suggestion_author, parent_doc):
        self.suggestion_highlight = suggestion_highlight
        self.suggestion_text = suggestion_text
        self.suggestion_author = suggestion_author
        self.parent_doc = parent_doc
    def __repr__(self):
        return f"<Suggestion {self.parent_doc.name}>"
    
class ChatMessage(db.Model):
    __tablename__ = "chatmessage"
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, ForeignKey("documents.id"))
    author = db.Column(db.Integer, ForeignKey("users.id"))
    message_author = relationship("User", back_populates="user_messages")
    parent_doc = relationship("Document", back_populates="messages")
    message = db.Column(db.String(1000))
    def __init__(self, message, message_author, parent_doc):
        self.message = message
        self.message_author = message_author
        self.parent_doc = parent_doc
    def __repr__(self):
        return f"<ChatMessage {self.message}>"
    
class EditRequest(db.Model):
    __tablename__ = "editrequest"
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, ForeignKey("documents.id"))
    author = db.Column(db.Integer, ForeignKey("users.id"))
    creator = relationship("User", back_populates="user_edits")
    editdoc = relationship("Document", back_populates="document_edits")
    content = db.Column(db.Text)
    def __init__(self, creator, editdoc, content):
        self.creator = creator
        self.editdoc = editdoc
        self.content = content
    def __repr__(self):
        return f"<EditRequest {self.id} @ {self.creator.username}>"

with app.app_context():
    db.create_all()
    ServerUser.query.delete()

my_email = "eitantravels25@gmail.com"
password = "lkmzeijqholesvam"
def sendemail(receiver, subject, message):
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as connection:
        connection.ehlo()
        connection.login(user=my_email, password=password)
        connection.sendmail(
            from_addr=my_email, 
            to_addrs=receiver, 
            msg=f"Subject:{subject}\n\n{message}"
        )

@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(int(user_id))

@app.route("/docs", methods=["GET", "POST"])
def docs():
    if current_user.is_authenticated:
        documents = Document.query.filter_by(creator_id=current_user.id).all()
        documentform = DocumentForm()
        if documentform.validate_on_submit() and len(documentform.name.data) <= 40:
            new_doc = Document(
                str(documentform.name.data),
                current_user.id,
                "",
                "Viewer",
                "Private",
                0
            )
            db.session.add(new_doc)
            db.session.commit()
            return redirect(url_for('docs'))
        return render_template("docs.html", current_user=current_user, documentform=documentform, documents=documents)
    else:
        return redirect(url_for('login'))

@app.route("/deletedoc/<id>", methods=["GET", "POST"])
def deletedoc(id):
    document = Document.query.filter_by(id=id).first()
    if document.creator.id == current_user.id:
        db.session.delete(document)
        db.session.commit()
        return redirect(url_for('docs'))
    else:
        return jsonify({"Cant delete document": "Not logged into user that hosts this document"})

@socketio.on("join")
def join(data):
    if current_user.is_authenticated and not ServerUser.query.filter_by(username=current_user.username, document_id=data[0]).first():
        doc = Document.query.get(data[0])
        doc.views += 1
        db.session.commit()
        room = str(data[0])
        join_room(room)
        new_user = ServerUser(
            current_user.username,
            current_user,
            doc,
            str(data[1])
        )
        db.session.add(new_user)
        db.session.commit()
        emit("join_room", current_user.username, broadcast=True, room=room, include_self=True)

@socketio.on("leave")
def leave(docid):
    pass

@socketio.on("disconnect")
def disconnect():
    sid = request.sid
    if ServerUser.query.filter_by(socket_id=sid).first():
        user = ServerUser.query.filter_by(socket_id=sid).first()
        docid = user.document_id
        username = user.username
        room = str(docid)
        leave_room(room)
        db.session.delete(user)
        db.session.commit()
        emit("disconnected_user", str(docid), broadcast=True, include_self=True)

@socketio.on("renew_text")
def renew_text(data):
    emit("renew_text", data, broadcast=True)

@app.route("/leave/<int:docid>/<int:userid>")
def user_leave(docid, userid):
    user = ServerUser.query.filter_by(username=User.query.get(userid).username).first()
    if user:
        db.session.delete(user)
        db.session.commit()  
    return redirect(url_for('home'))

@socketio.on("changetext")
def changetext(headers):
    emit("textchanger", headers['text'], broadcast=True, room=headers['room'], include_self=False)

@socketio.on("cursor_position")
def cursorpos():
    emit("cursor_position", broadcast=True)

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    data = request.get_json()
    content = data['content']
    # Create a PDF from the HTML content using WeasyPrint
    pdf = HTML(string=content).write_pdf(stylesheets=['static/style.css'])

    # Send the PDF as a downloadable file
    return send_file(BytesIO(pdf), as_attachment=True, download_name='content.pdf', mimetype='application/pdf')

@socketio.on("chat-send")
def chat_send(data):
    print(data)
    author = User.query.filter_by(username=data[1]).first()
    doc = Document.query.get(data[2])
    new_chat = ChatMessage(data[0], author, doc)
    db.session.add(new_chat)
    db.session.commit()
    emit("chat-send", data, broadcast=True, include_self=True)

@app.route("/changerole/<int:docid>")
def changerole(docid):
    print("Hello")
    doc = Document.query.get(docid)
    if doc.creator.id == current_user.id:
        username = json.loads(json.dumps(request.headers["username"]))
        if username == "lobal Role": username = "all"
        newrole = json.loads(json.dumps(request.headers["newrole"]))
        if Share.query.filter_by(document_id=doc.id, username=str(username)).first():
            share = Share.query.filter_by(document_id=doc.id, username=str(username)).first()
            share.role = newrole
            db.session.commit()
            return redirect(url_for("document", docid=doc.id))
    else:
        return jsonify({"Can't change role, you are not the owner of this document"})
    
@app.route("/getrole/<int:docid>")
def getrole(docid):
    username = request.headers["username"]
    document = Document.query.get(docid)
    if document.creator.username == username:
        return jsonify({"Role": "Owner"})
    else:
        if Share.query.filter_by(username="all", document_id=docid).first() and not Share.query.filter_by(username=username, document_id=docid).first():
            return jsonify({"Role": str(Share.query.filter_by(username="all", document_id=docid).first().role)})
        else:
            return jsonify({"Role": Share.query.filter_by(username=username, document_id=docid).first().role})
    
@app.route("/getusers/<int:docid>")
def getusers(docid):
    doc = Document.query.get(docid)
    list_of_users = []
    for i in ServerUser.query.filter_by(document_id=docid).all():
        if i.username == doc.creator.username:
            list_of_users.append(f"@{i.username} - Owner")
        else:
            if Share.query.filter_by(username="all", document_id=docid).first() and not Share.query.filter_by(username=i.username, document_id=docid).first():
                list_of_users.append(f"@{i.username} - {Share.query.filter_by(username='all', document_id=docid).first().role}")
            else:
                list_of_users.append(f"@{i.username} - {Share.query.filter_by(username=i.username, document_id=docid).first().role}")
    return jsonify({"Users": list_of_users})

@app.route("/share-default-role/<int:docid>", methods=["POST"])
def setdefaultrole(docid):
    doc = Document.query.get(docid)
    if doc.creator.id == current_user.id:
        role = request.headers["role"]
        doc.default_role = role
        db.session.commit()
        return redirect(url_for('document', docid=doc.id))
    else:
        return jsonify({"Can't set default role": "Current User isn't the owner of this document"})
    
@app.route("/set-document-privacy/<int:docid>", methods=["POST"])
def setdocumentprivacy(docid):
    doc = Document.query.get(docid)
    if doc.creator.id == current_user.id:
        privacy = str(request.headers["privacy"])
        if privacy == "Private" and doc.privacy != "Private" and Share.query.filter_by(document_id=doc.id, username="all").first():
            doc.privacy = "Private"
            db.session.commit()
            set_private = Share.query.filter_by(document_id=doc.id, username="all").first()
            db.session.delete(set_private)
            db.session.commit()
        elif privacy == "Public" and doc.privacy != "Public" and not Share.query.filter_by(document_id=doc.id, username="all").first():
            doc.privacy = "Public"
            db.session.commit()
            new_privacy = Share(
                "all",
                current_user,
                doc,
                str(doc.default_role)
            )
            db.session.add(new_privacy)
            db.session.commit()
        return redirect(url_for('document', docid=doc.id))
    else:
        jsonify({"Can't set the document privacy": "You aren't the owner of this document"})

# use fetch in the background to update the text every now and then
@app.route("/docs/<int:docid>/", methods=["GET", "POST"])
def document(docid):
    if current_user.is_authenticated:
        shareform = ShareForm()
        firstdocument = Document.query.get(docid)
        shares = Share.query.filter_by(document_id=docid).all()
        suggestion = Suggestion.query.filter_by(document_id=docid).all()
        if request.method == "POST":
            if shareform.validate_on_submit():
                if Share.query.filter_by(document_id=docid, username=str(shareform.username.data)).first() or current_user.username == str(shareform.username.data):
                    flash("User is already added to document")
                elif not User.query.filter_by(username=str(shareform.username.data)).first():
                    flash("User doesn't exist")
                else:
                    new_share = Share(
                        str(shareform.username.data),
                        current_user,
                        firstdocument,
                        str(firstdocument.default_role)
                    )
                    db.session.add(new_share)
                    db.session.commit()
                    return redirect(url_for('document', docid=docid))
        if firstdocument and firstdocument.creator_id == current_user.id or firstdocument and Share.query.filter_by(document_id=docid, username=current_user.username).first() != None or firstdocument and Share.query.filter_by(document_id=docid, username="all").first():
            if ServerUser.query.filter_by(username=current_user.username, document_id=docid).first():
                return render_template("launched.html", current_user=current_user)
            else:
                return render_template("pythondoc.html", firstdocument=firstdocument, current_user=current_user, shareform=shareform, shares=shares, suggestions=suggestion, chatmsgs=ChatMessage.query.filter_by(document_id=docid).all(), Share=Share, users=ServerUser.query.filter_by(document_id=docid).all(), EditRequest=EditRequest)
        else:
            return render_template("404.html")
    else:
        return redirect(url_for('login'))
    
@app.route("/docs/edit/<int:editid>")
def edit(editid):
    firstdocument = EditRequest.query.get(editid)
    if firstdocument and firstdocument.creator.username == current_user.username or firstdocument and firstdocument.editdoc.creator.id == current_user.id:
        return render_template("commit.html", firstdocument=firstdocument)
    else:
        return jsonify({"Can't open commit": "User logged in isn't owner"})

@app.route("/create-edit/<int:docid>")
def createedit(docid):
    doc = Document.query.get(docid)
    if Share.query.filter_by(document_id=docid, username=current_user.username).first() and Share.query.filter_by(document_id=docid, username=current_user.username).first().role == "Editor"  or not Share.query.filter_by(document_id=docid, username=current_user.username).first() and Share.query.filter_by(document_id=docid, username='all').first().role == "Editor" and not Document.query.get(docid).creator.id == current_user.id:
        new_edit = EditRequest(
            current_user, 
            doc,
            doc.content
        )
        db.session.add(new_edit)
        db.session.commit()
        return redirect(url_for('edit', editid=new_edit.id))
    else:
        return jsonify({"Permission denied": "You don't have permission to do this action with your current role, only allowed for editors (not owners)"})
    
@app.route("/docs/<int:docid>/edits")
def edits(docid):
    doc = Document.query.get(docid)
    editdocs = EditRequest.query.filter_by(editdoc=doc, creator=current_user)
    return render_template("edits.html", doc=doc, editdocs=editdocs)

@app.route("/docs/edit/delete/<int:editid>")
def deleteedit(editid):
    doc = EditRequest.query.get(editid)
    if doc and doc.creator.username == current_user.username or doc and doc.editdoc.creator.username == current_user.username:
        db.session.delete(doc)
        db.session.commit()
        return redirect(url_for("document", docid=doc.editdoc.id))
    else:
        return jsonify({"Cannot delete commit": "User not accessed or doesn't exist"})
    
@app.route("/docs/push/<int:docid>/<int:editid>")
def pushedit(docid, editid):
    doc = Document.query.get(docid)
    edit = EditRequest.query.get(editid)
    if doc.creator.username == current_user.username and edit.editdoc.id == doc.id:
        doc.content = edit.content
        db.session.delete(edit)
        db.session.commit()
        return redirect(url_for('document', docid=doc.id))
    else:
        return jsonify({"Can't push commit": "Not permitted access"})
    
@app.route("/docs/getcommits/<int:docid>")
def getcommits(docid):
    doc = Document.query.get(docid)
    editdoc = EditRequest.query.filter_by(editdoc=doc).all()
    editdocs = []
    for i in editdoc:
        editdocs.append([i.id, i.creator.username])
    return jsonify({"Data": editdocs})

@app.route("/suggestiondone/<int:suggestid>/<int:docid>")
def suggestiondone(suggestid, docid):
    document = Document.query.get(docid)
    if document.creator.id == current_user.id or Share.query.filter_by(document_id=docid, username=current_user.username).first() and Share.query.filter_by(document_id=docid, username=current_user.username).first().role == "Editor":
        suggestion = Suggestion.query.get(suggestid)
        suggestion.done = True
        db.session.commit()
        return redirect(url_for('document', docid=docid))
    else:
        return jsonify({"Can't resolve this suggestion": "Not logged into right account"})

@app.route("/removesuggestion/<int:suggestid>/<int:docid>")
def removesuggestion(suggestid, docid):
    document = Document.query.get(docid)
    if document.creator.id == current_user.id or Share.query.filter_by(document_id=docid, username=current_user.username).first() and Share.query.filter_by(document_id=docid, username=current_user.username).first().role == "Editor":
        suggestion = Suggestion.query.get(suggestid)
        db.session.delete(suggestion)
        db.session.commit()
        return redirect(url_for('document', docid=docid))
    else:
        return jsonify({"Can't remove suggestion": "Not logged into right account"})

@app.route("/addsuggestion/<int:docid>")
def addsuggestion(docid):
    if Share.query.filter_by(document_id=docid, username=current_user.username).first() != None or not Share.query.filter_by(document_id=docid, username=current_user.username).first() and Share.query.filter_by(document_id=docid, username='all').first().role == "Suggestor" and not Document.query.get(docid).creator.id == current_user.id:
        doc = Document.query.get(docid)
        highlighted_text = request.headers["highlighted_text"]
        text = request.headers["text"]
        new_suggestion = Suggestion(
            str(highlighted_text),
            str(text),
            current_user,
            doc
        )
        db.session.add(new_suggestion)
        db.session.commit()
        return redirect(url_for('document', docid=doc.id))
    return jsonify({"Can't add suggestion": "Not an editor of this document"})
 
@app.route("/docs/shared", methods=["GET", "POST"])
def shared():
    if current_user.is_authenticated:
        shared_docs = Share.query.filter_by(username=current_user.username).all()
        return render_template("shared.html", shared_docs=shared_docs, length=Share.query.filter_by(username=current_user.username).count())
    else:
        return redirect(url_for('login'))
    
class BrowseForm(FlaskForm):
    search = StringField("Search PyDocs:")
    submit = SubmitField("Search")
    
@app.route("/docs/browse", methods=["GET", "POST"])
def browse():
    searchform = BrowseForm()
    if current_user.is_authenticated:
       if searchform.validate_on_submit():
           docs = Document.query.filter_by(privacy="Public").filter(Document.name.like(f"%{str(searchform.search.data)}%")).order_by(Document.views.desc()).all()
           return render_template("browse.html", current_user=current_user, docs=docs, searchform=searchform)
       else:
            docs = Document.query.filter_by(privacy="Public").order_by(Document.views.desc()).all()
            return render_template("browse.html", current_user=current_user, docs=docs, searchform=searchform)
    else:
        return redirect(url_for('login'))

@app.route("/removeshare/<int:doc>/<int:shareid>")
def removeshare(doc, shareid):
    document = Document.query.get(doc)
    if document.creator.id == current_user.id:
        share = Share.query.get(shareid)
        if share:
            db.session.delete(share)
            db.session.commit()
            return redirect(url_for('document', docid=doc))
    else:
        return jsonify({"Can't Remove Share": "User not logged into proposed account"})

@app.route("/save", methods=["GET", "POST"])
def save():
    document = Document.query.get(int(request.args["id"]))
    if request.headers["text"]:
        document.content = request.headers["text"]
        db.session.commit()
    return redirect(url_for('document', docid=document.id))

@app.route("/saveedit", methods=["GET", "POST"])
def saveedit():
    editdoc = EditRequest.query.get(int(request.args["id"]))
    if request.headers["text"]:
        editdoc.content = request.headers["text"]
        db.session.commit()
    return redirect(url_for("edit", editid=editdoc.id))

@app.route("/renamedoc/<id>/<name>", methods=["GET", "POST"])
def renamedoc(id, name):
    document = Document.query.filter_by(id=id).first()
    if document.creator.id == current_user.id:
        document.name = name
        db.session.commit()
        return redirect(url_for('docs'))
    else:
        return jsonify({"Can't rename document": "Not logged into proposed account"})

@app.route("/")
def home():
    if not current_user.is_authenticated:
        return render_template("index.html", current_user=current_user)
    else:
        return redirect(url_for('docs'))

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if not current_user.is_authenticated:
        if request.method == "POST":
            if form.validate_on_submit():
                username = str(form.username.data)
                password = str(form.password.data)
                user = User.query.filter_by(username=username).first()
                if not user:
                    flash("This account doesn't exist, please try again.")
                elif not check_password_hash(user.password, password):
                    flash("The password is incorrect, please try again.")
                else:
                    login_user(user)
                    return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))
                    
    return render_template("login.html", form=form, current_user=current_user)

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if not current_user.is_authenticated:
        if request.method == "POST":
            if form.validate_on_submit():
                username = str(form.username.data)
                if db.session.query(User).filter_by(username=username).count() < 1 and username != "all":
                    new_user = User(
                        str(username),
                        str(generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8))
                    )
                    db.session.add(new_user)
                    db.session.commit()
                    login_user(new_user)
                    return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))
    return render_template("register.html", form=form, current_user=current_user)

@app.route("/sendcontactres", methods=["POST"])
def contactres():
    if request.method == "POST" and str(request.form["first-name"]) != "" and str(request.form["last-name"]) != "" and str(request.form["email"]) != "" and str(request.form["phone"]) != "" and str(request.form["message"]) != "":
       sendemail("eitantravels25@gmail.com", "Contact Note from PyDocs", f"From {request.form['first-name']} {request.form['last-name']} at {request.form['email']}, Phone Number: {request.form['phone']},\n{request.form['message']}")
    return redirect('/#contact')

@app.route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=8080)