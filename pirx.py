#!/usr/bin/env python

import copy
import collections
import itertools
import math

import pygame


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_COLOR_DEPTH = 32


class Planet(object):
    def __init__(self, position, mass, radius, speed):
        self.position = position
        self.mass = mass
        self.color = pygame.color.Color("red")
        self.radius = radius
        self.speed = speed

    def draw(self):
        screen_position = (int(self.position[0]), int(self.position[1]))
        pygame.draw.circle(screen, self.color, screen_position, self.radius)


class SpaceShip(object):

    future_image = pygame.Surface((1, 1))
    future_image.fill(pygame.color.Color("white"))

    def __init__(self, position, speed, rgb):
        self.position = position
        self.speed = speed
        self.radius = 2
        self.mass = 1.0
        self.rgb = rgb
        self.color = pygame.color.Color(rgb[0], rgb[1], rgb[2], 255)

    def draw(self):
        screen_position = (int(self.position[0]), int(self.position[1]))
        pygame.draw.circle(screen, self.color, screen_position, self.radius)

    def draw_future(self, how_far):
        screen_position = (int(self.position[0]), int(self.position[1]))
        self.future_image.fill(self.color)
        self.future_image.set_alpha(int(96 - 96 * how_far))
        pygame.Surface.blit(screen, self.future_image, screen_position)

class Statistics(object):
    def __init__(self):
        self.sample_count = 100
        self.samples = [0.0] * self.sample_count
        self.sum_of_samples = 0.0
        self.reset()

    def push(self, sample):
        self.sum_of_samples -= self.samples.pop(0)
        self.sum_of_samples += sample
        self.samples.append(sample)
        self.max_sample = max(sample, self.max_sample)
        self.min_sample = min(sample, self.min_sample)

    @property
    def moving_avg(self):
        return self.sum_of_samples / float(self.sample_count)

    def reset(self):
        self.max_sample = 0.0
        self.min_sample = 2**31


XYValue = collections.namedtuple('XYValue', 'x y v')
XY = collections.namedtuple('XY', 'x y')


class World(object):
    def __init__(self):
        self.planets = [Planet((SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2), 100, 20, (-0.2, 0))]
        self.planets.append(Planet((SCREEN_WIDTH / 2, SCREEN_HEIGHT / 1.3), 20, 5, (1.0, 0)))
        self.spaceships = []
        ship_position = (self.planets[0].position[0] + SCREEN_WIDTH / 4, self.planets[0].position[1] + SCREEN_HEIGHT / 4)
        ship_speed = (0.2, -0.5)
        ship = SpaceShip(ship_position, ship_speed, (0, 255, 0))
        self.spaceships = [ship]

        self.random_spaceships()
        self.color_of_space = pygame.color.Color("black")
        self.deferred_actions = []
    
    def random_spaceships(self):
        import random
        count = 10
        for _ in range(count):
            ship_position = (SCREEN_WIDTH * random.random(), SCREEN_HEIGHT * random.random())
            ship_speed = (random.random() - 0.5,  random.random() - 0.5)
            rgb = tuple(int(c) for c in (random.random() * 255, random.random() * 255, random.random() * 255))
            ship = SpaceShip(ship_position, ship_speed, rgb=rgb)
            self.spaceships.append(ship)

    class DestroyShipLater(object):
        def __init__(self, world, spaceship):
            self.spaceship = spaceship
            self.world = world
        
        def do(self):
            print "Boom"
            self.world.spaceships.remove(self.spaceship)

    def tick(self):
        self.simulate_ships()
        self.process_waiting()
        self.simulate_planets()
        return self

    def process_waiting(self):
        for action in self.deferred_actions:
            action.do()
        self.deferred_actions = []

    def distance(self, obj1, obj2):
        x = obj1.position[0] - obj2.position[0]
        y = obj1.position[1] - obj2.position[1]
        euclidean = math.sqrt(x**2 + y**2)
        return XYValue(x, y, euclidean)

    def gravity_force(self, obj1, obj2, distance):
        forcex = math.copysign(1.0 / distance.v**2 * obj1.mass * obj2.mass, distance.x)
        forcey = math.copysign(1.0 / distance.v**2 * obj1.mass * obj2.mass, distance.y)
        return XY(forcex, forcey)

    def simulate_ships(self):
        for spaceship in self.spaceships:
            spaceship.position = (
                spaceship.position[0] + spaceship.speed[0],
                spaceship.position[1] + spaceship.speed[1]
            )

            forcex, forcey = 0.0, 0.0
            for planet in self.planets:
                distance = self.distance(planet, spaceship)

                if distance.v < planet.radius:
                    self.deferred_actions.append(World.DestroyShipLater(self, spaceship))

                force = self.gravity_force(planet, spaceship, distance)
                forcex += force.x
                forcey += force.y

            spaceship.speed = (spaceship.speed[0] + forcex, spaceship.speed[1] + forcey)

    def simulate_planets(self):
        for planet1, planet2 in itertools.product(self.planets, self.planets):
            if planet1 == planet2: continue
            forcex, forcey = 0.0, 0.0
            distance = self.distance(planet2, planet1)

            force = self.gravity_force(planet1, planet2, distance)
            forcex += force.x
            forcey += force.y

            planet1.speed = (planet1.speed[0] + forcex / planet1.mass, planet1.speed[1] + forcey / planet1.mass)

        self.move_planets()

    def move_planets(self):
        for planet in self.planets:
            planet.position = (
                planet.position[0] + planet.speed[0],
                planet.position[1] + planet.speed[1]
            )

    def draw(self):
        for planet in self.planets:
            planet.draw()
        for spaceship in self.spaceships:
            spaceship.draw()

    def draw_future(self, how_far):
        for spaceship in self.spaceships:
            spaceship.draw_future(how_far)

def setup_screen():
    global screen
    pygame.init()
    pygame.display.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF, SCREEN_COLOR_DEPTH)


def game_loop(world):
    framerate_limit = 60
    framerate_limiter = pygame.time.Clock()
    frame_timer = pygame.time.Clock()
    current_frame = 0
    frame_statistics = Statistics()

    future_step_count = 500
    futures = [world]
    for _ in range(future_step_count):
        futures.append(copy.deepcopy(futures[-1]).tick())

    while True:
        frame_timer.tick()
        current_world = futures.pop(0)
        screen.fill(current_world.color_of_space)
        current_world.draw()

        for future_idx, future in enumerate(futures):
            future.draw_future(float(future_idx) / future_step_count)

        futures.append(copy.deepcopy(futures[-1]).tick())
        pygame.display.flip()
        frame_timer.tick()

        frame_time = frame_timer.get_time()
        frame_statistics.push(frame_time)
        framerate_limiter.tick(framerate_limit)
        current_frame += 1

        if current_frame % framerate_limit == 0:
            print "Frame time avg", frame_statistics.moving_avg
            print "Frame time min", frame_statistics.min_sample
            print "Frame time max", frame_statistics.max_sample
            print "FPS:", framerate_limiter.get_fps()
            current_frame = 0
            frame_statistics.reset()


if __name__ == '__main__':
    setup_screen()
    world = World()
    game_loop(world)

