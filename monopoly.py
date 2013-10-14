#!/usr/bin/python3
#-*- encodig: utf-8 -*-

import time
import random

from yaml import load_all as yamlopen
from colors import cprintln as cprint, register_tag


register_tag('game', fg="black")
register_tag('dice', fg="red")
register_tag('player', fg="blue", bg="white")
register_tag('move', bg="blue", fg="white")
register_tag('field', style="bold", bg="white")

register_tag('red', fg="red")
register_tag('lightblue', fg=87, bg=241)
register_tag('darkblue', fg=21)
register_tag('lila', fg=93, bg=241)
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


def register(registry, name):
    def decorator(fn):
        registry[name] = fn
        return fn

    return decorator


def payRentIsNessesary(field, player, game):
    if field.owner and field.owner != player:
        rent = field.currentRent() #  emit charge money
        game.transferMoney(player, field.owner, rent)


fieldevents = {}


@register(fieldevents, "visitNormalStreet")
def ons(field, player, game):
    payRentIsNessesary(field, player, game)


@register(fieldevents, "visitTrainStation")
def onts(field, player, game):
    pass


@register(fieldevents, "visitGotoJail")
def vgj(field, player, game):


@register(fieldevents, "visitTax")
def onTax(field, player, game):
    print("visit tax field %s" % field.name)


class Dice(object):
    def __init__(self):
        self.eyes = ( self.throw(), self.throw() )

    def doubles(self):
        a, b = self.eyes
        return a == b

    def count(self):
        return sum(self.eyes)

    def throw(self):
        return random.randint(1, 6)


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
        self.insert(0, a)

    def pushBack(self, a):
        self.insert(len(self), a)


class Field(object):
    def __init__(self, field, config):
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
        self.attr.update((self.typeObj))
        self.attr.update((self.familyObj))
        self.attr.update((field))

        self.owner = None

    def tryCall(self, attr, player, game):
        try:
            name = self.attr[attr]
            fieldevents[name](self, player, game)
        except KeyError:
            pass

    def onPassing(self, player, game):
        self.tryCall('on_pass', player, game)

    def onVisit(self, player, game):
        cprint("{game %s visits %s" % (player, self))
        self.tryCall('on_visit', player, game)

    def __str__(self):
        return "{field {%s %s}}" % ( self.family, self.name )

    def __repr__(self):
        return str(self)


def translate(config):
    def forField(field):
        return Field(field, config)

    return list(map(forField, config['fields']))


def first(itr):
    """return first element of the iter """
    return next(iter(itr))


class Game(object):
    def __init__(self, path):
        with open(path) as yf:
            self.cfg = first(yamlopen(yf))

        self.fields = translate(self.cfg)
        self.turnQueue = DQueue()
        self.playerPositions = {}
        self.maxfield = len(self.cfg['fields'])
        self.lastDice = None
        self.jailDoublesCounter = 0
        self.accounts = {'bank': 0, 'freepark': 0}
        self.injail = set()

    def addPlayer(self, player):
        self.playerPositions[player] = 0
        self.turnQueue.pushBack(player)
        self.accounts[player] = 0
        self.transferMoney('bank', player, self.cfg['startmoney'])

    def nextTurn(self):
        self.lastDice = dice = Dice()
        currentPlayer = self.turnQueue.popFront()

        cprint("{game Turn of {player %s}}" % currentPlayer.name)
        cprint("{game Throw the dice %s}" % str(dice.eyes))

        if dice.doubles():
            self.jailDoublesCounter += 1
            self.injail.discard(currentPlayer)

            if self.jailDoublesCounter >= self.cfg['doubles_jail_limit']:
                self.sendPlayerToJail(currentPlayer)
                return
            else:
                self.turnQueue.pushFront(currentPlayer)
        else:
            self.jailDoublesCounter = 0
            self.turnQueue.pushBack(currentPlayer)
            if currentPlayer in self.injail:
                return

        self.movePlayerForward(currentPlayer, dice.count())

        cprint("{game new turn queue: %s}" % self.turnQueue)
        currentPlayer(game)
        time.sleep(1)

    def transferMoney(self, sender, receiver, amount):
        self.accounts[sender] -= amount
        self.accounts[receiver] += amount

    def sendPlayerToJail(self, player):
        self.playerPositions[player] = self.cfg['jail_field']
        self.injail.add(player)

    def iter(self, a, b):
        for i in range(0, abs(a - b)):
            f = (a + i) % len(self.fields)
            yield self.fields[f]

    def triggerEvents(self, player, fromField, toField):
        for field in self.iter(fromField, toField):
            field.onPassing(player, self)
        self.fields[toField % len(self.fields)].onVisit(player, self)

    def movePlayerForward(self, player, number):
        curpos = self.playerPositions[player]
        nextpos = curpos + number
        cprint("{move {player %s} from %d to %d}" % (player, curpos, nextpos))
        self.playerPositions[player] = nextpos
        self.triggerEvents(player, curpos, nextpos)


    def transferOwnership(self, sender, receiver, field):
        field.owner = receiver

    def buyField(self, player, field):
        assert field.owner == None
        self.transferMoney(player, BANK, field.buyprice)
        self.transferOwnership(BANK, player, field)

    def buyHouse(self, player, field):
        assert field.owner == player


BANK = 'bank'


class DummyPlayer(object):
    def __init__(self):
        self.name = "dummy"

    def __call__(self, game):
        pass

    def __str__(self): return "{player %s}" % self.name

    def __repr__(self): return str(self)


if __name__ == "__main__":
    game = Game("monopoly.field.yaml")
    game.addPlayer(DummyPlayer())

    for j in range(1, 10):
        game.nextTurn()
