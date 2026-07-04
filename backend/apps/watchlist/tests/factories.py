import factory
from factory.django import DjangoModelFactory

from apps.basedata.tests.factories import PersonFactory
from apps.watchlist.models import Watchlist, WatchlistEntry


class WatchlistFactory(DjangoModelFactory):
    class Meta:
        model = Watchlist

    name = factory.Sequence(lambda n: f"Watchlist {n:03d}")
    list_type = Watchlist.ListType.CRIMINAL


class WatchlistEntryFactory(DjangoModelFactory):
    class Meta:
        model = WatchlistEntry

    watchlist = factory.SubFactory(WatchlistFactory)
    person = factory.SubFactory(PersonFactory)
    reason = "Armed robbery suspect"
