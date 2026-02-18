from app.extensions import db


class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(300), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    published_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<BlogPost {self.slug}>"
