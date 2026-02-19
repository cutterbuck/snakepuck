#!/bin/bash
flask db upgrade
python -m scripts.seed_blog_posts
