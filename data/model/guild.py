import mongoengine
from data.model.filterword import FilterWord
from data.model.tag import Tag

class Guild(mongoengine.Document):
    _id                       = mongoengine.IntField(required=True)
    case_id                   = mongoengine.IntField(min_value=1, required=True)
    reaction_role_mapping     = mongoengine.DictField()
    role_administrator        = mongoengine.IntField()
    role_nerds                = mongoengine.IntField()
    role_moderator            = mongoengine.IntField()
    role_mute                 = mongoengine.IntField()
    role_birthday             = mongoengine.IntField()
    role_helpers              = mongoengine.IntField()
    role_rules                = mongoengine.IntField()
    role_timeout              = mongoengine.IntField()
    
    channel_offtopic          = mongoengine.IntField()
    channel_modlogs           = mongoengine.IntField()
    channel_private           = mongoengine.IntField()
    channel_reaction_roles    = mongoengine.IntField()
    channel_reports           = mongoengine.IntField()
    channel_support           = mongoengine.IntField()
    channel_deals             = mongoengine.IntField()

    emoji_logging_webhook     = mongoengine.IntField()
    filter_excluded_channels  = mongoengine.ListField(default=[])
    filter_excluded_guilds    = mongoengine.ListField(default=[253908290105376768])
    filter_words              = mongoengine.EmbeddedDocumentListField(FilterWord, default=[])
    raid_phrases              = mongoengine.EmbeddedDocumentListField(FilterWord, default=[])
    logging_excluded_channels = mongoengine.ListField(default=[])
    locked_channels           = mongoengine.ListField(default=[])
    tags                      = mongoengine.EmbeddedDocumentListField(Tag, default=[])
    ban_today_spam_accounts   = mongoengine.BooleanField(default=False)

    meta = {
        'db_alias': 'default',
        'collection': 'guilds'
    }

