from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """ ใช้ดึงค่าจาก dict ใน template """
    return dictionary.get(key)
