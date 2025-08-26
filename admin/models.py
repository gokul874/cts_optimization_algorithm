from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ProviderNetwork(db.Model):
    __tablename__ = 'provider_network'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    contact_number = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<ProviderNetwork {self.name}>'