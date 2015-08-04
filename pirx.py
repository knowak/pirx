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


class SpaceShip(object):
    def __init__(self, position, speed, rgb):
        self.position = position
        self.speed = speed
        self.radius = 2
        self.mass = 1.0
        self.rgb = rgb
        self.color = pygame.color.Color(rgb[0], rgb[1], rgb[2], 255)


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
        for d in range(count):
            planet = random.choice(self.planets)
            planet = self.planets[1]
            ship_position = (planet.radius*d + planet.position[0] + planet.radius * random.random(), planet.radius*d + planet.position[1] + planet.radius * random.random())
            ship_speed = (random.random() * 1.3*planet.speed[0], planet.speed[1] * 1.1)
            rgb = tuple(int(c) for c in (random.random() * 255, random.random() * 255, random.random() * 255))
            ship = SpaceShip(ship_position, ship_speed, rgb=rgb)
            self.spaceships.append(ship)

    class DestroyShipLater(object):
        def __init__(self, world, spaceship):
            self.spaceship = spaceship
            self.world = world
        
        def do(self):
            print("Boom")
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

class Viewport(object):

    spaceship_future_image = pygame.Surface((1, 1))
    spaceship_future_image.fill(pygame.color.Color("white"))
    SCROLL_STEP = 100
    ZOOM_STEP = 2.0

    def __init__(self, simulation, screen):
        self.simulation = simulation
        self.screen = screen
        self.coordinates = (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.zoom = 1.0


    def draw(self):
        current_world = self.simulation.current_world
        screen.fill(current_world.color_of_space)
        self.draw_world()

        for future_idx, future in enumerate(self.simulation.futures):
            progress = float(future_idx) / self.simulation.future_step_count
            self.draw_future(future, progress)
        pygame.display.flip()

    def draw_world(self):
        for planet in self.simulation.current_world.planets:
            self.draw_planet(planet)
        for spaceship in self.simulation.current_world.spaceships:
            self.draw_spaceship(spaceship)

    def draw_future(self, future, how_far):
        for spaceship in future.spaceships:
            self.draw_future_spaceship(spaceship, how_far)

    def draw_planet(self, planet):
        radius = int(planet.radius * self.zoom)

        pygame.draw.circle(self.screen, planet.color, self.screen_position(planet.position), radius)

    def draw_spaceship(self, spaceship):
        pygame.draw.circle(self.screen, spaceship.color, self.screen_position(spaceship.position), spaceship.radius)

    def draw_future_spaceship(self, spaceship, how_far):
        self.spaceship_future_image.fill(spaceship.color)
        self.spaceship_future_image.set_alpha(int(96 - 80 * how_far))
        pygame.Surface.blit(self.screen, self.spaceship_future_image, self.screen_position(spaceship.position))

    def screen_position(self, position):
        pos_x = (position[0] - self.coordinates[0]) * self.zoom
        pos_y = (position[1] - self.coordinates[1]) * self.zoom
        return (int(pos_x), int(pos_y))

    def left(self):
        self.coordinates = (
            self.coordinates[0] - self.SCROLL_STEP * (1.0 / self.zoom),
            self.coordinates[1],
            self.coordinates[2],
            self.coordinates[3]
        )

    def right(self):
        self.coordinates = (
            self.coordinates[0] + self.SCROLL_STEP * (1.0 / self.zoom),
            self.coordinates[1],
            self.coordinates[2],
            self.coordinates[3]
        )

    def up(self):
        self.coordinates = (
            self.coordinates[0], 
            self.coordinates[1] - self.SCROLL_STEP * (1.0 / self.zoom), 
            self.coordinates[2],
            self.coordinates[3]
        )

    def down(self):
        self.coordinates = (
            self.coordinates[0], 
            self.coordinates[1] + self.SCROLL_STEP * (1.0 / self.zoom), 
            self.coordinates[2], 
            self.coordinates[3]
        )

    def zoom_in(self):
        self.zoom *= self.ZOOM_STEP

    def zoom_out(self):
        self.zoom /= self.ZOOM_STEP

class Simulation(object):
    def __init__(self, world):
        self.world = world
        self.future_step_count = 500
        self._futures = [world]
        for _ in range(self.future_step_count):
            self._futures.append(copy.deepcopy(self._futures[-1]).tick())

    def tick(self):
        self._futures.append(copy.deepcopy(self._futures[-1]).tick())
        self._futures.pop(0)

    @property
    def current_world(self):
        return self._futures[0]

    @property
    def futures(self):
        return self._futures[1:]


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

    simulation = Simulation(world)
    viewport = Viewport(simulation, screen)

    while True:
        frame_timer.tick()
        event = pygame.event.poll()

        while event.type != pygame.NOEVENT:
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    viewport.left()
                elif event.key == pygame.K_RIGHT:
                    viewport.right()
                elif event.key == pygame.K_UP:
                    viewport.up()
                elif event.key == pygame.K_DOWN:
                    viewport.down()
                elif event.key == pygame.K_MINUS:
                    viewport.zoom_out()
                elif event.key == pygame.K_EQUALS:
                    viewport.zoom_in()
            event = pygame.event.poll()

        viewport.draw()
        simulation.tick()
        frame_timer.tick()

        frame_time = frame_timer.get_time()
        frame_statistics.push(frame_time)
        framerate_limiter.tick(framerate_limit)
        current_frame += 1

        if current_frame % framerate_limit == 0:
            print("Frame time avg", frame_statistics.moving_avg)
            print("Frame time min", frame_statistics.min_sample)
            print("Frame time max", frame_statistics.max_sample)
            print("FPS:", framerate_limiter.get_fps())
            current_frame = 0
            frame_statistics.reset()


if __name__ == '__main__':
    setup_screen()
    world = World()
    game_loop(world)

