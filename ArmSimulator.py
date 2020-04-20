import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from Arm import *

class ArmSimulator(Arm):
    def __init__(self, port_handler, packet_handler):
        self.dhp = np.mat([[0, 0, 18.5, 0.1381482112],
                           [0, 22.3, 0, 1.5],
                           [-np.pi / 2, 25.3, 0, 0],
                           [np.pi / 2, 6.5, -1.5, 0],
                           [0, 6, 0, 0],
                           [0, 0, -15.5, 0]])
        self.init_vis()
        self.set_thetas(self.get_thetas())
        try:
            Arm.__init__(self, port_handler, packet_handler)
        except:
            self.motor_list = []

    def init_vis(self):
        self.t0 = np.empty((self.dhp.shape[0], 4, 4))
        self.z0 = np.empty((self.dhp.shape[0], 4, 4))  # Z-axis matrices for each joint
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(211, projection='3d')
        self.ep = self.fig.add_subplot(212, aspect="equal")
        # ax.view_init(50, azim=90)

        # Label the figure and axes (including units)
        self.ax.set_title("Arm Dynamics")
        self.ax.set_xlabel("X0 (cm)")
        self.ax.set_ylabel("Y0 (cm)")
        self.ax.set_zlabel("Z0 (cm)")

        # Fix axis limits so that they're the same size regardless of
        # the configuration of the arm
        self.ax.set_xlim((0, 50))
        self.ax.set_ylim((-50, 50))
        self.ax.set_zlim((0, 20))
        self.ep.set_xlim((0, 50))
        self.ep.set_ylim((0, 50))
        self.arm_objects = [[], []]
        color_codes = ('#DAF7A6', '#FFC300', '#FF5733', '#C70039', '#900C3F', '#581845')
        for i in range(1, self.t0.shape[0]):
            self.arm_objects[0].extend(
                self.ax.plot([self.t0[i - 1][0][3], self.t0[i][0][3]], [self.t0[i - 1][1][3], self.t0[i][1][3]],
                             [self.t0[i - 1][2][3], self.t0[i][2][3]],
                             'o-', linewidth=5, color=color_codes[-i - 1]))

        for i in range(self.t0.shape[0]):
            self.arm_objects[1].extend(
                self.ax.plot([self.t0[i][0][3], self.z0[i][0][3]], [self.t0[i][1][3], self.z0[i][1][3]],
                             [self.t0[i][2][3], self.z0[i][2][3]], '-',
                             markersize=5, linewidth=1, label="z{0}".format(i + 1), color=color_codes[-i - 1]))
        plt.ion()
        plt.show()


    def visualizeArm(self):
        '''Draw a stick figure of the the arm in its current configuration.

        t0 is a numpy ndarray of shape (N, 4, 4), where N is the number of
        degrees of freedom. t0[i][:][:] is the transformation
        matrix describing the position and orientation of frame i in frame 0.

        Similarly, z0 is a numpy ndarray of shape (N, 4, 4), where N is the
        number of degrees of freedom. z0[i][:][:] is the transformation
        matrix describing the position and orientation of the end of the Zi
        axis in frame 0.

        All angles must be in radians and all distances must be in cm.'''

        # Draw the links of the arm

        for i, line in zip(range(1, self.t0.shape[0]), self.arm_objects[0]):
            line.set_data([self.t0[i - 1][0][3], self.t0[i][0][3]], [self.t0[i - 1][1][3], self.t0[i][1][3]])
            line.set_3d_properties([self.t0[i - 1][2][3], self.t0[i][2][3]])

        for i, line in zip(range(self.t0.shape[0]), self.arm_objects[1]):
            line.set_data([self.t0[i][0][3], self.z0[i][0][3]], [self.t0[i][1][3], self.z0[i][1][3]])
            line.set_3d_properties([self.t0[i][2][3], self.z0[i][2][3]])

        self.ep.scatter(self.t0[-1][0][3], self.t0[-1][1][3], color='#B0B0B0', s=1)
        self.ax.scatter(self.t0[-1][0][3], self.t0[-1][1][3], self.t0[-1][2][3], color='#B0B0B0', s=1)

        plt.pause(0.00025)

    def set_thetas(self, position=(0, 0, 0, 0), wait=False):
        a1, a2, a3, a4 = position
        # print (position)
        self.dhp[:, 3] = (np.mat([a1, a2, a3, a4, 0, 0])).T

        for i in range(self.dhp.shape[0]):
            # Create joint transformation from DH Parameters
            self.t0[i] = np.mat([(np.cos(self.dhp[i,3]), -np.sin(self.dhp[i,3]), 0, self.dhp[i,1]),
                                 (np.sin(self.dhp[i,3])*np.cos(self.dhp[i, 0]), np.cos(self.dhp[i,3])*np.cos(self.dhp[i,0]),
                                  -np.sin(self.dhp[i,0]), -self.dhp[i, 2] * np.sin(self.dhp[i, 0])),
                                 (np.sin(self.dhp[i,3]) * np.sin(self.dhp[i, 0]), np.cos(self.dhp[i, 3]) * np.sin(self.dhp[i, 0]),
                                  np.cos(self.dhp[i,0]), self.dhp[i, 2] * np.cos(self.dhp[i, 0])),
                                 (0, 0, 0, 1)])

            # Put each transformation in the frame 0
            if i != 0:
                self.t0[i] = np.matmul(self.t0[i - 1], self.t0[i])

            # Compute Z axis in frame 0 for each joint
            self.z0[i] = np.matmul(self.t0[i], np.mat([[1, 0, 0, 0],
                                                       [0, 1, 0, 0],
                                                       [0, 0, 1, 5],
                                                       [0, 0, 0, 1]]))
        # self.visualizeArm()

    def get_thetas(self):
        return self.dhp[0, 3], self.dhp[1, 3], self.dhp[2, 3], self.dhp[3, 3]

    def close_connection(self):
        return

    def get_ea(self):
        return self.t0[-1][0][3], self.t0[-1][1][3], self.t0[-1][1][3]

    def get_xy(self):
        return self.t0[-1][0][3], self.t0[-1][1][3]