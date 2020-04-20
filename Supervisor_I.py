# Supervisor.py
# Spring 2020
# Ben Webb

from Arm import *
from dynamixelSDK.src.dynamixel_sdk import PortHandler, PacketHandler
import time

np.set_printoptions(precision=5, suppress=True)


def step(p1, p2, x, y, s):
    """
     Follows the linear equations
     X Axis:  P1 = -5.3439414 * X + 1136.064 - P2
              P2 = -0.1240340 * X **2 + -8.7340980 * y + 897.655633
     Y Axis:  P1 = 9.1529305 * Y + 149.1745896
              P2 = -0.1194068 * Y**2 + -5.8520929 * X + 828.9275838
    :param t1:
    :param t2:
    :param x:
    :param y:
    :param s:
    :return:
    """
    return np.array((p1, p2)) + np.array(
        ((-5.3439414 + 0.248068 * x, 9.1529305),
         (-0.248068 * x, -0.2388136 * y))
    ) @ s


class PID:
    def __init__(self, pos):
        """
        Y-motor primitive
        px, ix, dx = 0.0132, 0.00014, 0.01
        py, iy, dy = 0.0064, 0.00025, 0.0047
        """
        px, ix, dx = 0.074765625, 0.0002, 0.220625
        py, iy, dy = 0.0671875, 0.00025, 0.218

        self.pid = np.array(((0.0, 0.0, 0.0),
                             (0.0, 0.0, 0.0)))

        self.pid_weights = np.array(((px, py),
                                     (ix, iy),
                                     (dx, dy)))

        self.pid_abs_error = np.array((0.0, 0.0))
        self.pos = np.array(pos)

    def update_origin(self, pos):
        self.pos = np.array(pos)

    def update_pid_weight(self, px, ix, dx, py, iy, dy):
        self.pid = np.array(((0.0, 0.0, 0.0),
                             (0.0, 0.0, 0.0)))
        self.pid_weights = np.array(((px, py),
                                     (ix, iy),
                                     (dx, dy)))
        self.pid_abs_error = np.array((0.0, 0.0))

    def update_pid(self, pos, d):
        residuals = self.pos - pos
        self.pos += d

        self.pid[:, 2] = residuals - self.pid[:, 0]
        self.pid[:, 0] = residuals
        self.pid[:, 1] += residuals

        self.pid_abs_error += abs(residuals)

        result = self.pid @ self.pid_weights

        return np.array((result[0, 0], result[1, 1]))


class Supervisor:
    def __init__(self):
        import sys
        import os
        if sys.platform == 'linux':
            port_handler = PortHandler('/dev/ttyACM0')
        else:
            port_handler = PortHandler('/dev/' + os.listdir('/dev')[-2])
        packet_handler = PacketHandler(1.0)

        try:
            port_handler.openPort()
            port_handler.setBaudRate(1000000)
        except OSError:
            _ = None

        self.arm = Arm(port_handler, packet_handler)

        self.apply_pressure = False
        self.pid = PID(self.arm.get_xy())

    def move(self, d, steps=400, step_time=0.005):
        """
        :param d:
        :param steps:
        :param step_time:
        :return:
        """
        p1, p2, p3, p4 = self.arm.get_positions()
        p4 = 512
        i = 0
        while i < steps:
            _ = time.perf_counter() + step_time
            x, y = self.arm.get_xy()
            s = d * (np.cos(np.pi*i/steps+np.pi)+1)
            pid = self.pid.update_pid(np.array((x, y)), s)
            p1, p2 = step(p1, p2, x, y, s + pid)
            if self.apply_pressure:
                p3 = 512
            self.arm.set_positions((p1, p2, p3, p4))
            i += 1
            while time.perf_counter() < _:
                pass
        time.sleep(0.4)
        return i

    def pressure(self):
        self.apply_pressure = True
        a1, a2, a3, a4 = self.arm.get_positions()
        self.arm.set_positions((a1, a2, 512, a4))
        time.sleep(0.6)

    def train_pid(self):
        prev_error_x, prev_error_y = 10000.0, 10000.0

        px, ix, dx = 0.007000, 0.00003, 0.005037
        py, iy, dy = 0.005177, 0.00001, 0.00270

        vx, vy = 0.001, 0.001

        for j in range(10):
            self.pid.update_pid_weight(px, ix, dx, py, iy, dy)
            # self.pid.update_origin(self.arm.get_xy())
            r = 0
            for f in range(2):
                r += self.move(np.array([ 0.00,  0.025]))
                r += self.move(np.array([ 0.025,  0.00]))
                r += self.move(np.array([ 0.00, -0.025]))
                r += self.move(np.array([-0.025,  0.00]))
                # r += self.move(np.array([ 0.025,  0.00]))
                # r += self.move(np.array([ 0.00,  0.025]))
                # r += self.move(np.array([-0.025,  0.00]))
                # r += self.move(np.array([ 0.00, -0.025]))



            print(
                  "%.8f %.8f %.6f %.6f %.6f %.6f %.6f %.6f" %
                  (*(self.pid.pid_abs_error / r).tolist(), px, ix, dx, py, iy, dy))

            if self.pid.pid_abs_error[0]/r < prev_error_x:
                dx += vx
                vx /= 2
            else:
                dx -= vx
                vx *= -1

            if self.pid.pid_abs_error[1]/r < prev_error_y:
                dy += vy
                vy /= 2
            else:
                dy -= vy
                vy *= -1

            prev_error_x, prev_error_y = self.pid.pid_abs_error / r


'''
643.8830877189278 303.72287507548714 10000 10000 0.0075 0.005
696.453379797246 307.69105620247564 643.8830877189278 303.72287507548714 0.0125 0.01
719.1808566471108 324.40590987080543 696.453379797246 307.69105620247564 0.01 0.0075
705.868515423729 324.5148855639921 719.1808566471108 324.40590987080543 0.0125 0.01
728.8244944673896 337.6749557419218 705.868515423729 324.5148855639921 0.015000000000000001 0.0075

0.46996680 0.47318441 0.00500 0.00000 0.00220 0.00150 0.00000 0.00110
0.42030037 0.30397424 0.00500 0.00000 0.00270 0.00150 0.00000 0.00160
0.47279692 0.31583070 0.00500 0.00000 0.00295 0.00150 0.00000 0.00185
0.47127508 0.33234551 0.00500 0.00000 0.00283 0.00150 0.00000 0.00172
0.43922467 0.30536477 0.00500 0.00000 0.00270 0.00150 0.00000 0.00185
0.40998432 0.30491520 0.00500 0.00000 0.00264 0.00150 0.00000 0.00198
0.39439062 0.29559661 0.00500 0.00000 0.00261 0.00150 0.00000 0.00204
0.41306375 0.28868056 0.00500 0.00000 0.00259 0.00150 0.00000 0.00207
0.41786780 0.28694614 0.00500 0.00000 0.00260 0.00150 0.00000 0.00208
0.42054947 0.34659056 0.00500 0.00000 0.00259 0.00150 0.00000 0.00209

0.46088514 0.24785328 0.00500 0.00000 0.00260 0.00150 0.00000 0.00208
0.48746732 0.24273448 0.00510 0.00000 0.00260 0.00160 0.00000 0.00208
0.47956108 0.24669842 0.00505 0.00000 0.00260 0.00165 0.00000 0.00208
0.51094401 0.24468197 0.00500 0.00000 0.00260 0.00162 0.00000 0.00208
0.48934883 0.26720067 0.00503 0.00000 0.00260 0.00160 0.00000 0.00208
0.50339880 0.24947273 0.00505 0.00000 0.00260 0.00161 0.00000 0.00208
0.47852467 0.24437587 0.00504 0.00000 0.00260 0.00162 0.00000 0.00208
0.47598820 0.26329172 0.00502 0.00000 0.00260 0.00163 0.00000 0.00208
0.45237502 0.26916721 0.00502 0.00000 0.00260 0.00163 0.00000 0.00208
0.51974882 0.27134092 0.00502 0.00000 0.00260 0.00163 0.00000 0.00208

0.48695793 0.30458314 0.00502 0.00001 0.00260 0.00163 0.00001 0.00208
0.46719501 0.42058786 0.00502 0.00002 0.00260 0.00163 0.00002 0.00208
0.45079472 0.33820897 0.00502 0.00003 0.00260 0.00163 0.00002 0.00208
0.40557133 0.28543828 0.00502 0.00003 0.00260 0.00163 0.00001 0.00208
0.43498817 0.32718758 0.00502 0.00003 0.00260 0.00163 0.00001 0.00208
0.42085486 0.31168317 0.00502 0.00003 0.00260 0.00163 0.00001 0.00208
0.46989095 0.32822550 0.00502 0.00003 0.00260 0.00163 0.00001 0.00208
0.44819912 0.36604331 0.00502 0.00003 0.00260 0.00163 0.00001 0.00208
0.44145286 0.34223696 0.00502 0.00003 0.00260 0.00163 0.00001 0.00208
0.38791984 0.34973114 0.00502 0.00003 0.00260 0.00163 0.00001 0.00208

0.41522840 0.21887038 0.00502 0.00003 0.002600 0.001630 0.00001 0.00208
0.37692482 0.27164277 0.00502 0.00003 0.003600 0.001630 0.00001 0.00308
0.37958812 0.22572004 0.00502 0.00003 0.004100 0.001630 0.00001 0.00258
0.37484665 0.26155028 0.00502 0.00003 0.003850 0.001630 0.00001 0.00208
0.39732353 0.21706915 0.00502 0.00003 0.003600 0.001630 0.00001 0.00233
0.38065857 0.20999026 0.00502 0.00003 0.003725 0.001630 0.00001 0.00258
0.37821544 0.20906885 0.00502 0.00003 0.003850 0.001630 0.00001 0.00270
0.36078353 0.23295346 0.00502 0.00003 0.003912 0.001630 0.00001 0.00277
0.38837039 0.22753862 0.00502 0.00003 0.003944 0.001630 0.00001 0.00274
0.39094840 0.26133627 0.00502 0.00003 0.003928 0.001630 0.00001 0.00270

0.37896089 0.25639254 0.00502 0.00003 0.003912 0.001630 0.00001 0.00270
0.32788777 0.22813436 0.00602 0.00003 0.003912 0.002630 0.00001 0.00270
0.38326536 0.18436255 0.00652 0.00003 0.003912 0.003130 0.00001 0.00270
0.33432872 0.18992730 0.00627 0.00003 0.003912 0.003380 0.00001 0.00270
0.38243670 0.16835535 0.00602 0.00003 0.003912 0.003255 0.00001 0.00270
0.38576211 0.18513771 0.00614 0.00003 0.003912 0.003130 0.00001 0.00270
0.37804508 0.18494384 0.00602 0.00003 0.003912 0.003193 0.00001 0.00270
0.40588419 0.17771794 0.00589 0.00003 0.003912 0.003255 0.00001 0.00270
0.40976448 0.20078930 0.00596 0.00003 0.003912 0.003286 0.00001 0.00270
0.38857670 0.16611136 0.00589 0.00003 0.003912 0.003271 0.00001 0.00270

0.36447927 0.21356784 0.00502 0.00003 0.003912 0.003271 0.00001 0.00270
0.34475730 0.17507821 0.00602 0.00003 0.003912 0.004271 0.00001 0.00270
0.33641832 0.17455551 0.00652 0.00003 0.003912 0.004771 0.00001 0.00270
0.31095328 0.15863153 0.00677 0.00003 0.003912 0.005021 0.00001 0.00270
0.29927448 0.15852475 0.00690 0.00003 0.003912 0.005146 0.00001 0.00270
0.29297853 0.15988414 0.00696 0.00003 0.003912 0.005209 0.00001 0.00270
0.29692056 0.14558157 0.00699 0.00003 0.003912 0.005177 0.00001 0.00270
0.32735334 0.15468232 0.00697 0.00003 0.003912 0.005146 0.00001 0.00270
0.29904374 0.16225937 0.00699 0.00003 0.003912 0.005162 0.00001 0.00270
0.29072260 0.15246693 0.00700 0.00003 0.003912 0.005146 0.00001 0.00270

'''

if __name__ == "__main__":
    sup = Supervisor()
    sup.pressure()
    t = time.time()
    sup.train_pid()
    try:
        print("Time: ", time.time() - t)
    finally:
        sup.arm.close_connection()
