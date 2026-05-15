import pytest

from app.items import ItemStore


def test_add_and_list():
    store = ItemStore()
    a = store.add("widget", 9.99)
    b = store.add("gadget", 12.50)
    assert a.id == 1
    assert b.id == 2
    assert [i.name for i in store.list()] == ["widget", "gadget"]


def test_get_returns_none_for_missing():
    store = ItemStore()
    assert store.get(999) is None


def test_delete_returns_true_when_present():
    store = ItemStore()
    item = store.add("widget", 1.0)
    assert store.delete(item.id) is True
    assert store.delete(item.id) is False


def test_add_rejects_empty_name():
    store = ItemStore()
    with pytest.raises(ValueError):
        store.add("", 1.0)
    with pytest.raises(ValueError):
        store.add("   ", 1.0)


def test_add_rejects_negative_price():
    store = ItemStore()
    with pytest.raises(ValueError):
        store.add("widget", -1.0)


def test_clear_resets_ids():
    store = ItemStore()
    store.add("a", 1.0)
    store.clear()
    new_item = store.add("b", 2.0)
    assert new_item.id == 1
