"""Web frontend for motor-blog: actually show web pages to visitors
"""

import tornado.web
from tornado import gen
import motor

from models import Post, Category


# TODO: document this as a means of refactoring
@gen.engine
def get_categories(db, callback):
    try:
        # TODO: cache
        category_docs = yield motor.Op(
            db.categories.find().sort('name').to_list)

        categories = [Category(**doc) for doc in category_docs]
        callback(categories, None)
    except Exception, e:
        callback(None, e)


class HomeHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @gen.engine
    def get(self, page_num=0):
        postdocs = yield motor.Op(
            self.settings['db'].posts.find({'status': 'Published'})
                .sort([('date_created', -1)])
                .skip(int(page_num) * 10)
                .limit(10)
                .to_list)

        posts = [Post(**postdoc) for postdoc in postdocs]
        categories = yield motor.Op(get_categories, self.settings['db'])
        self.render(
            'home.html',
            posts=posts, categories=categories, page_num=int(page_num))


class PostHandler(tornado.web.RequestHandler):
    """Show a single blog post"""
    @tornado.web.asynchronous
    @gen.engine
    def get(self, slug):
        postdoc = yield motor.Op(
            self.settings['db'].posts.find_one,
                {'slug': slug, 'status': 'Published'})

        if not postdoc:
            raise tornado.web.HTTPError(404)

        post=Post(**postdoc)

        prevdoc = yield motor.Op(
            self.settings['db'].posts.find_one,
            {
                'status': 'Published',
                'date_created': {'$lte': post['date_created']},
                '_id': {'$ne': post.id }
            })
        prev = Post(**prevdoc) if prevdoc else None

        nextdoc = yield motor.Op(
            self.settings['db'].posts.find_one,
            {
                'status': 'Published',
                'date_created': {'$gte': post['date_created']},
                '_id': {'$ne': post.id }
            })
        next = Post(**nextdoc) if nextdoc else None

        categories = yield motor.Op(get_categories, self.settings['db'])
        self.render(
            'single.html',
            post=post, prev=prev, next=next, categories=categories)

class CategoryHandler(tornado.web.RequestHandler):
    """Page of posts for a category"""
    @tornado.web.asynchronous
    @gen.engine
    def get(self, category_name, page_num=0):
        # TODO: index
        postdocs = yield motor.Op(
            self.settings['db'].posts
            .find({'status': 'Published', 'categories.name': category_name})
            .sort([('date_created', -1)])
            .limit(10)
            .to_list)

        posts = [Post(**postdoc) for postdoc in postdocs]
        categories = yield motor.Op(get_categories, self.settings['db'])
        self.render(
            'category.html',
            posts=posts, categories=categories)

class MediaHandler(tornado.web.RequestHandler):
    """Retrieve media object, like an image"""
    @tornado.web.asynchronous
    @gen.engine
    def get(self, url):
        # TODO: index url
        media = yield motor.Op(
            self.settings['db'].media.find_one, {'url': url})

        if not media:
            raise tornado.web.HTTPError(404)

        self.set_header('Content-Type', media['type'])
        self.write(media['content'])
        self.finish()

class RemoveSlashHandler(tornado.web.RequestHandler):
    def get(self, slug):
        self.redirect('/' + slug.rstrip('/'), permanent=True)