#!/usr/bin/env python

import itertools
import math

import pygame

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

class Planet(object):
    def __init__(self, position, mass, radius, speed):
        self.position = position
        self.mass = mass
        self.color = pygame.color.Color("red")
        self.screen = screen
        self.radius = radius
        self.speed = speed

    def draw(self):
        screen_position = (int(self.position[0]), int(self.position[1]))
        pygame.draw.circle(self.screen, self.color, screen_position, self.radius)


class SpaceShip(object):
    def __init__(self, position, speed, color=pygame.color.Color("green")):
        self.position = position
        self.speed = speed
        self.color = color
        self.radius = 2
        global screen
        self.screen = screen

    def draw(self):
        screen_position = (int(self.position[0]), int(self.position[1]))
        pygame.draw.circle(self.screen, self.color, screen_position, self.radius)


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


class World(object):
    def __init__(self):
        global screen
        self.screen = screen
        self.planets = [Planet((SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2), 100, 20, (0.0, 0))]
        self.planets.append(Planet((SCREEN_WIDTH / 2, SCREEN_HEIGHT / 1.3), 20, 5, (0.4, 0)))
        self.spaceships = []
        ship_position = (self.planets[0].position[0] + SCREEN_WIDTH / 4, self.planets[0].position[1] + SCREEN_HEIGHT / 4)
        ship_speed = (0.2, -0.5)
        ship = SpaceShip(ship_position, ship_speed)
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
            rgba = (random.random() * 255, random.random() * 255, random.random() * 255, 255)
            color = pygame.color.Color(*tuple(int(c) for c in rgba))

            ship = SpaceShip(ship_position, ship_speed, color=color)
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

    def process_waiting(self):
        for action in self.deferred_actions:
            action.do()
        self.deferred_actions = []

    def simulate_ships(self):
        for spaceship in self.spaceships:
            spaceship.position = (
                spaceship.position[0] + spaceship.speed[0],
                spaceship.position[1] + spaceship.speed[1]
            )

            forcex, forcey = 0.0, 0.0
            for planet in self.planets:
                distancex = planet.position[0] - spaceship.position[0]
                distancey = planet.position[1] - spaceship.position[1]
                distance = math.sqrt((distancex)**2 + (distancey)**2)

                if distance < planet.radius:
                    self.deferred_actions.append(World.DestroyShipLater(self, spaceship))

                forcex += math.copysign(1.0 / distance**2 * planet.mass, distancex)
                forcey += math.copysign(1.0 / distance**2 * planet.mass, distancey)

            spaceship.speed = (spaceship.speed[0] + forcex, spaceship.speed[1] + forcey)


    def simulate_planets(self):
        for planet1, planet2 in itertools.product(self.planets, self.planets):
            if planet1 == planet2: continue
            forcex, forcey = 0.0, 0.0
            distancex = planet2.position[0] - planet1.position[0]
            distancey = planet2.position[1] - planet1.position[1]
            distance = math.sqrt((distancex)**2 + (distancey)**2)

            forcex += math.copysign(1.0 / distance**2 * planet2.mass * planet1.mass / 10, distancex)
            forcey += math.copysign(1.0 / distance**2 * planet2.mass * planet1.mass / 10, distancey)

            planet1.speed = (planet1.speed[0] + forcex / planet1.mass, planet1.speed[1] + forcey / planet1.mass)

        for planet in self.planets:
            planet.position = (
                planet.position[0] + planet.speed[0],
                planet.position[1] + planet.speed[1]
            )


    def draw(self):
        self.screen.fill(self.color_of_space)
        for planet in self.planets:
            planet.draw()
        for spaceship in self.spaceships:
            spaceship.draw()
        pygame.display.flip()


def setup_screen():
    global screen
    pygame.init()
    pygame.display.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))


def game_loop(world):
    framerate_limit = 60
    framerate_limiter = pygame.time.Clock()
    frame_timer = pygame.time.Clock()
    current_frame = 0
    frame_statistics = Statistics()

    while True:
        frame_timer.tick()
        world.tick()
        world.draw()
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

