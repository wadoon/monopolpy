#!/usr/bin/python3
#-*- encodig: utf-8 -*-

import time
import random

from pprint import pprint
from yaml import load_all as yamlopen

try:
    from colors import cprintln as cprint, register_tag


    register_tag('game', fg="black")
    register_tag('dice', fg="red")
    register_tag('player', fg="blue", bg="white")
    register_tag('move', bg="blue", fg="white")
    register_tag('field', style="bold", bg="white")
    register_tag('debug', fg="red", style="bold")

    register_tag('money', fg="green", bg="yellow")

    register_tag('red', fg="red")
    register_tag('lightblue', fg=87, bg=241)
    register_tag('darkblue', fg=21)
    register_tag('lila', fg=93)
    register_tag('orange', fg=172)
    register_tag('green', fg=28)
    register_tag('pink', fg=207)
    register_tag('yellow', fg=226, bg=241)

    register_tag('tax')
    register_tag('trainstation')
    register_tag('freepark')
    register_tag('eventfield')
    register_tag('socialfield')
    register_tag('plants')
    register_tag('jail')
    register_tag('gotojail')
    register_tag('startfield')
except ImportError:
    cprint = print

def register( registry , name):
    def decorator(fn):
        registry[name] = fn
        return fn
    return decorator

class Dice(object):
    def __init__(self):
        self.eyes = ( self.throw(), self.throw() )

    def doubles(self):
        a,b = self.eyes
        return a == b

    def count(self):
        return sum(self.eyes)

    @staticmethod
    def throw():
        return random.randint(1,6)

class DQueue(list):
    def __init__(self, *args):
        list.__init__(self, *args)

    def popFront(self):
        a = self.peakFront()
        del self[0]
        return a

    def peakFront(self):
        return self[0]

    def peakBack(self):
        return self[-1]

    def popBack(self):
        a = self.peakBack()
        del self[-1]
        return a

    def pushFront(self, a):
        self.insert(0 , a)

    def pushBack(self, a):
        self.insert( len(self) , a)


FIELD_TYPES = {}
@register( FIELD_TYPES, "default")
class Field(object):
    def __init__(self, field, config):
        self.isBuildable = True
        self.name = field['name']

        self.family = field['family']
        try:
            self.familyObj = config['families'][self.family]
        except KeyError:
            self.familyObj = {}


        try:
            self.type = self.familyObj['type']
            self.typeObj = config['types'][self.type]
        except KeyError:
            self.typeObj = {}

        self.attr = dict()
        self.attr.update( (self.typeObj) )
        self.attr.update( (self.familyObj) )
        self.attr.update( (field) )

        self.owner = None
        self.get = self.attr.get

    def __getattr__(self, name):
        return self.get(name)


    def onPassing(self, player, game):
        pass

    def onVisit(self, player, game):
        pass

    def claimRent(self, rent, player, game):
        if self.owner and self.owner != player:
            game.transferMoney(player, self.owner, rent, "rent")

    def __str__(self):
        return "{field {%s %s}}" %( self.family, self.name )

    def __repr__(self): return str(self)

class Rentable(Field):
     def __init__(self, field, config):
        super().__init__(field, config)
        self.isBuildable = False
        self.isBuyable = True
        self.houseState = 0

@register( FIELD_TYPES, "normalstreet")
class StreetField(Rentable):
    def __init__(self, field, config):
        super().__init__(field, config)

    def buildHouse(self, amount):
        pass

    def currentRent(self, game):
        rents = self.get('rent')
        rent = rents[self.houseState]

        family = game.findFields(family = self.family)
        if all(map(lambda x: x.owner == self.owner, family)):
            rent *= 2
        return rent



    def onVisit(self, player, game):
        self.claimRent(self.currentRent(game), player, game)

@register( FIELD_TYPES, "trainstation")
class TrainStationField(Rentable):
    def onVisit(self, player, game):
        stations = filter(
            lambda f: f.owner == self.owner,
            game.findFields(type="trainstation"))
        factor = len(list(stations))
        self.claimRent(factor * self.get('base_rent'), player, game)



@register(FIELD_TYPES, "gotojail")
class GotoJailField(Field):
    def onVisit(self, player, game):
        game.sendPlayerToJail(player)

@register(FIELD_TYPES, "socialfield")
class SocialField(Field):
    def onVisit(self, player, game):
        amount = random.choice((50,100,150,200,250))
        giveOrTake = bool(random.randint(0,1))
        if giveOrTake:
            game.transferMoney(BANK, player, amount, 'social field')
        else:
            game.transferMoney(player, BANK,  amount, 'social field')

@register(FIELD_TYPES, "eventfield")
class EventField(SocialField):
    pass


@register(FIELD_TYPES, "freepark")
class FreePark(Field):
    def onVisit(self, player, game):
        amount = game.getMoney('freepark')
        if amount > 0:
            game.transferMoney('freepark', player, amount, "freepark hit")

@register(FIELD_TYPES, "plants")
class PlantsField(Rentable):
    def onVisit(self, player, game):
        dice = game.lastDice.count()
        factor, falternate = game.get('plantfactors')

        a,b = game.findFields( type = "plants" )
        if a.owner == b.owner:
            factor = falternate

        rent = factor * dice
        self.claimRent(rent, player, game)

@register(FIELD_TYPES, "tax")
class TaxField(Field):
    def onVisit(self, player, game):
        cprint("{game %s payes tax}" % player)
        game.transferMoney(player, 'freepark', game.get("tax"), 'tax')
        cprint("%s current money: %d" % (player, game.getMoney(player)) )
        cprint("%s current money: %d" % ('freepark', game.getMoney('freepark')) )

@register(FIELD_TYPES, "startfield")
class StartField(Field):
    def onPassing(self, player, game):
        cprint("{game %s passed the start field}" % player)
        game.transferMoney( BANK , player, game.get('startpassmoney'))
        cprint("%s current money: %d" % (player, game.getMoney(player)) )

def fieldConstruct(field, config):
    family = field['family']
    try:
        type = config['families'][family]['type']
    except:
        type = family

    if type in FIELD_TYPES:
        return FIELD_TYPES[type](field, config)
    else:
        return FIELD_TYPES["default"](field, config)

def translate(config):

    def forField(field):
        return fieldConstruct(field, config)
    return list( map(forField, config['fields']) )


def first(itr):
    """return first element of the iter """
    return next(iter(itr))

class Game(object):
    def __init__(self, path):
        with open(path) as yf:
            self.cfg = first( yamlopen( yf ) )

        self.fields = translate(self.cfg)
        self.turnQueue = DQueue()
        self.playerPositions = {}
        self.maxfield = len( self.cfg['fields'] )
        self.lastDice = None
        self.jailDoublesCounter = 0
        self.accounts = {BANK: 0, 'freepark': 0}
        self.injail = {}

        self.maxHouses = self.get("available_houses")
        self.countHouses = 0
        self.maxHotels = self.get("available_hotels")
        self.countHotels = 0

    def get(self, key):
        return self.cfg[key]

    def findFields(self, name = None, type = None, family = None):
        def eq(a,b):
            if a is None or b is None:
                return True
            else:
                return a == b

        def pred(f):
            return eq(name, f.get("name") ) and eq(type, f.get("type")) and eq(type, f.get("family"))

        return list(filter(pred, self.fields))


    def addPlayer(self, player):
        self.playerPositions[player] = 0
        self.turnQueue.pushBack(player)
        self.accounts[player] = 0
        self.transferMoney(BANK, player,  self.cfg['startmoney'])

    def getMoney(self,player): return self.accounts[player]

    def nextTurn(self):
        self.lastDice = dice =  Dice()
        currentPlayer = self.turnQueue.popFront()

        cprint("{game Turn of {player %s}}" % currentPlayer.name)
        cprint("{game Throw the dice %s}" % str(dice.eyes) )

        if dice.doubles():
            self.jailDoublesCounter += 1

            if currentPlayer in self.injail:
                del self.injail[currentPlayer]

            if self.jailDoublesCounter >= self.cfg['doubles_jail_limit']:
                self.sendPlayerToJail( currentPlayer )
                self.jailDoublesCounter = 0
                self.turnQueue.pushBack(currentPlayer)
                return
            else:
                self.turnQueue.pushFront(currentPlayer)
        else:
            self.jailDoublesCounter = 0
            self.turnQueue.pushBack(currentPlayer)
            if currentPlayer in self.injail:
                if self.injail[currentPlayer] < self.get('jail_tries'):
                    return
                else:
                    self.transferMoney(currentPlayer, BANK, self.get("jail_fee"))

        self.movePlayerForward( currentPlayer, dice.count() )

        cprint("{game new turn queue: %s}" % self.turnQueue )
        currentPlayer( game )
        #time.sleep(1)

    def transferMoney(self, sender, receiver, amount, reason = "" ):
        cprint("{money transfer $ %d from %s to %s} %s" % (amount, sender, receiver, reason))

        self.accounts[sender] -= amount
        self.accounts[receiver] += amount

    def sendPlayerToJail(self, player):
        self.playerPositions[player] = self.cfg['jail_field']
        self.injail[player] = 0

    def iter(self, a, b):
        for i in range(0, abs( a - b)):
            f = (a + i)  % len(self.fields)
            yield self.fields[f]

    def triggerEvents(self, player, fromField, toField):
        for field in self.iter(fromField, toField):
            field.onPassing(player, self)
        self.fields[toField % len(self.fields) ].onVisit(player, self)

    def movePlayerForward(self, player, number):
        curpos = self.playerPositions[player]
        nextpos = curpos + number
        cprint("{move {player %s} from %d to %d}" % (player, curpos, nextpos))
        self.playerPositions[player] = nextpos
        self.triggerEvents(player, curpos, nextpos)

    def transferOwnership(self, sender, receiver, field):
            if sender != BANK and field.owner != None:
                assert field.owner == sender
            field.owner = receiver

    def buyField(self, player, field):
        assert field.owner is None
        self.transferMoney(player, BANK, field.get('buyprice'))
        self.transferOwnership(BANK, player, field)

    def buyHouses(self, player, field, amount):
        assert field.owner == player
        #TODO implement this thing


    def getField(self, player):
        return self.fields[ self.playerPositions[player] % len(self.fields) ]

    def isBuyable(self, field):
        return field.owner is None and isinstance(field, Rentable) and 'buyprice' in field.attr

BANK = 'bank'

class DummyPlayer(object):
    def __init__(self, n = "dummy"):
        self.name = n

    def __call__(self, game):
        pass

    def __str__(self): return "{player %s}" % self.name
    def __repr__(self): return str(self)


class PlayerBuyEverything(DummyPlayer):
    def __init__(self, n = "buyer"):
        super().__init__(n)

    def __call__(self, game):
        f = game.getField(self)
        cprint(str(f))
        print(repr(f.get('buyprice')))
        if game.isBuyable(f) and game.getMoney(self) >= f.get('buyprice'):
            game.buyField(self, f)



if __name__ == "__main__":
    game = Game("monopoly.field.yaml")
    game.addPlayer(PlayerBuyEverything("p1"))
    game.addPlayer(DummyPlayer("p2"))
    game.addPlayer(DummyPlayer("p3"))
    game.addPlayer(PlayerBuyEverything("p4"))

    for j in range(1,1000):
        game.nextTurn()

    pprint(game.accounts)

    for f in game.fields:
        if f.owner is not None:
            cprint( "%s\t\t\t%s" % (str(f), f.owner))
        else:
            cprint(str(f))
