import json

from scrapy import Request, Spider

from weibo.items import *


class WeiboSpider(Spider):
    name = 'weibocn'
    allowed_domains = ['m.weibo.cn']
    start_urls = ['http://m.weibo.cn/']
    
    user_url = 'https://m.weibo.cn/api/container/getIndex?uid={uid}&type=uid&value={uid}&containerid=100505{uid}'
    
    follow_url = 'https://m.weibo.cn/api/container/getIndex?containerid=231051_-_followers_-_{uid}&uid={uid}&page={page}'
    
    fan_url = 'https://m.weibo.cn/api/container/getIndex?containerid=231051_-_fans_-_{uid}&uid={uid}&page={page}'
    
    weibo_url = 'https://m.weibo.cn/api/container/getIndex?uid={uid}&type=uid&page={page}&containerid=107603{uid}'
    
    comment_url = 'https://m.weibo.cn/api/comments/show?id={id}&page={page}'
    
    repost_url = 'https://m.weibo.cn/api/statuses/repostTimeline?id={id}&page={page}'
    
    start_users = ['3217179555', '1742566624', '2282991915', '1288739185', '3952070245', '5878659096']
    
    def start_requests(self):
        for uid in self.start_users:
            yield Request(self.user_url.format(uid=uid), callback=self.parse_user)
    
    def parse_user(self, response):
        self.logger.debug(response)
        result = json.loads(response.text)
        if result.get('userInfo'):
            user_info = result.get('userInfo')
            user_item = UserItem()
            field_map = {
                'id': 'id', 'name': 'screen_name', 'avatar': 'profile_image_url', 'cover': 'cover_image_phone',
                'gender': 'gender', 'description': 'description', 'fans_count': 'followers_count',
                'follows_count': 'follow_count', 'weibos_count': 'statuses_count', 'verified': 'verified',
                'verified_reason': 'verified_reason', 'verified_type': 'verified_type'
            }
            for field, attr in field_map.items():
                user_item[field] = user_info.get(attr)
            
            yield user_item
            # 关注
            uid = user_info.get('id')
            yield Request(self.follow_url.format(uid=uid, page=1), callback=self.parse_follows,
                          meta={'page': 1, 'uid': uid})
            # 粉丝
            yield Request(self.fan_url.format(uid=uid, page=1), callback=self.parse_fans,
                          meta={'page': 1, 'uid': uid})
            # 微博
            yield Request(self.weibo_url.format(uid=uid, page=1), callback=self.parse_weibos,
                          meta={'page': 1, 'uid': uid})
    
    def parse_follows(self, response):
        result = json.loads(response.text)
        if result.get('ok') and result.get('cards') and len(result.get('cards')) and result.get('cards')[-1].get(
            'card_group'):
            # 解析用户
            follows = result.get('cards')[-1].get('card_group')
            for follow in follows:
                if follow.get('user'):
                    user_id = follow.get('user').get('id')
                    yield Request(self.user_url.format(uid=user_id), callback=self.parse_user)
            
            uid = response.meta.get('uid')
            
            user_relation_item = UserRelationItem()
            print(follows)
            follows = [{'id': follow.get('user').get('id'), 'name': follow.get('user').get('screen_name')} for follow in
                       follows]
            user_relation_item['id'] = uid
            user_relation_item['follows'] = follows
            user_relation_item['fans'] = []
            yield user_relation_item
            # 下一页关注
            page = response.meta.get('page') + 1
            yield Request(self.follow_url.format(uid=uid, page=page),
                          callback=self.parse_follows, meta={'page': page, 'uid': uid})
    
    def parse_fans(self, response):
        result = json.loads(response.text)
        if result.get('ok') and result.get('cards') and len(result.get('cards')) and result.get('cards')[-1].get(
            'card_group'):
            # 解析用户
            fans = result.get('cards')[-1].get('card_group')
            for fan in fans:
                if fan.get('user'):
                    user_id = fan.get('user').get('id')
                    yield Request(self.user_url.format(uid=user_id), callback=self.parse_user)
            
            uid = response.meta.get('uid')
            
            user_relation_item = UserRelationItem()
            fans = [{'id': fan.get('user').get('id'), 'name': fan.get('user').get('screen_name')} for fan in
                    fans]
            user_relation_item['id'] = uid
            user_relation_item['fans'] = fans
            user_relation_item['follows'] = []
            yield user_relation_item
            # 下一页粉丝
            page = response.meta.get('page') + 1
            yield Request(self.fan_url.format(uid=uid, page=page),
                          callback=self.parse_fans, meta={'page': page, 'uid': uid})
    
    def parse_weibos(self, response):
        result = json.loads(response.text)
        if result.get('ok') and result.get('cards'):
            weibos = result.get('cards')
            for weibo in weibos:
                mblog = weibo.get('mblog')
                if mblog:
                    weibo_item = WeiboItem()
                    field_map = {
                        'id': 'id', 'attitudes_count': 'attitudes_count', 'comments_count': 'comments_count',
                        'reposts_count': 'reposts_count', 'picture': 'original_pic', 'pictures': 'pics',
                        'source': 'source', 'text': 'text', 'raw_text': 'raw_text', 'thumbnail': 'thumbnail_pic'
                    }
                    for field, attr in field_map.items():
                        weibo_item[field] = mblog.get(attr)
                    weibo_item['user'] = response.meta.get('uid')
                    yield weibo_item
            # 下一页微博
            uid = response.meta.get('uid')
            page = response.meta.get('page') + 1
            yield Request(self.weibo_url.format(uid=uid, page=page), callback=self.parse_weibos,
                          meta={'uid': uid, 'page': page})
