import pygame
from collections import deque
import random
import numpy as np
from scipy.ndimage import label, binary_erosion

# 初始化pygame
pygame.init()

# 定义窗口尺寸
WIDTH, HEIGHT = 800, 600

TIME_HORIZON = 50  # 预测未来 50 帧
GRID_SIZE = 10

window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.init()
pygame.display.set_caption("Ball Avoidance Game-1024客户运营部技术节")

# 定义颜色
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (125, 150, 0)
GREEN = (0, 255, 0)
# 小球半径 
BALL_RADIUS = 20

# 定义小球类
class Ball:
    def __init__(self):
        self.position = np.array([WIDTH // 2, HEIGHT // 2], dtype=float)
        self.radius = BALL_RADIUS
        self.speed = 20

    def move_towards(self, target_position):
        """ 在四个方向（上、下、左、右）中选择最接近目标点的方向 """
        move_options = {
            "up": np.array([0, -self.speed]),
            "down": np.array([0, self.speed]),
            "left": np.array([-self.speed, 0]),
            "right": np.array([self.speed, 0])
        }

        # 计算球朝向目标点的四个方向的欧几里得距离
        best_direction = "stay"
        min_distance = np.linalg.norm(self.position - target_position)

        for direction, move_vector in move_options.items():
            new_position = self.position + move_vector
            distance = np.linalg.norm(new_position - target_position)

            if distance < min_distance:
                min_distance = distance
                best_direction = direction

        # 执行移动
        if best_direction != "stay":
            self.position += move_options[best_direction]

        self.position[0] = max(self.radius, min(self.position[0], WIDTH - self.radius))
        self.position[1] = max(self.radius, min(self.position[1], HEIGHT - self.radius))

    def draw(self, surface):
        pygame.draw.circle(surface, BLUE, (self.position[0], self.position[1]), self.radius)
    
    def __repr__(self) -> str:
        return f"({self.position[0]}, {self.position[1]})"


# 定义障碍物类
class Obstacle:
    def __init__(self):
        self.position = np.array([random.randint(0, WIDTH), 0], dtype=float)
        self.square_length = BALL_RADIUS * 2
        self.speed = 2

    def fall(self):
        self.position[1] += self.speed

    def draw(self, surface):
        pygame.draw.rect(surface, RED, (self.position[0], self.position[1],
                         self.square_length, self.square_length))

    def __repr__(self) -> str:
        return f"({self.position[0]}, {self.position[1]})"

    def predict_position(self, t):
        """ 预测 t 帧后的位置 """
        return self.position + np.array([0, self.speed * t])


def generate_safe_map(ball, obstacles):
    """
    生成未来 TIME_HORIZON 帧的 "安全区域地图"
    """
    safe_map = np.ones((WIDTH // GRID_SIZE, HEIGHT // GRID_SIZE))

    for t in range(TIME_HORIZON):
        for obs in obstacles:
            future_pos = obs.predict_position(t)  # 预测 t 帧后的矩形位置
            left = future_pos[0]
            right = future_pos[0] + obs.square_length
            top = future_pos[1]
            bottom = future_pos[1] + obs.square_length

            for grid_x in range(int(left // GRID_SIZE), int(right // GRID_SIZE) + 1):
                for grid_y in range(int(top // GRID_SIZE), int(bottom // GRID_SIZE) + 1):
                    if grid_x < safe_map.shape[0] and grid_y < safe_map.shape[1]:
                        safe_map[grid_x, grid_y] = 0  # 占据的地方标记为危险

    return safe_map


def apply_erosion(safe_map, structure_size=2):
    """
    对安全区域进行腐蚀，去除狭长的连通区域
    """
    structure = np.ones((structure_size, structure_size))  # 结构元素
    eroded_map = binary_erosion(safe_map, structure).astype(int)
    return eroded_map


def find_largest_safe_zone(safe_map):
    """ 识别最大连通安全区域，并返回其中心点 """
    labeled_map, num_features = label(safe_map)  # 计算连通区域
    if num_features == 0:
        return np.array([WIDTH / 2, HEIGHT - 20])  # 没有安全区域，返回默认点

    # 统计每个连通区域的大小
    sizes = np.bincount(labeled_map.ravel())[1:]  # 跳过背景（0）
    largest_label = np.argmax(sizes) + 1  # 找到最大区域的索引（跳过背景）

    # 找到最大区域的像素点
    safe_positions = np.argwhere(labeled_map == largest_label)
    center = np.mean(safe_positions, axis=0) * GRID_SIZE  # 计算中心点

    return center


def draw_safe_map(safe_map: np.array, surface):
    for dx in range(safe_map.shape[0]):
        for dy in range(safe_map.shape[1]):
            Color = YELLOW if safe_map[dx, dy] == 0 else GREEN
            pygame.draw.rect(surface, Color, (dx * GRID_SIZE, dy * GRID_SIZE,
                                    GRID_SIZE, GRID_SIZE))


# 检测碰撞，考虑球的半径
def is_colliding(ball, obstacle):
    # 计算小木块的边界
    left = obstacle.position[0]
    right = obstacle.position[0] + obstacle.square_length
    top = obstacle.position[1]
    bottom = obstacle.position[1] + obstacle.square_length

    # 计算小球的边界
    ball_radius = ball.radius
    ball_left = ball.position[0] - ball_radius
    ball_right = ball.position[0] + ball_radius
    ball_top = ball.position[1] - ball_radius
    ball_bottom = ball.position[1] + ball_radius

    # 检查小球是否与小木块重叠
    return (ball_right >= left and 
            ball_left <= right and 
            ball_bottom >= top and 
            ball_top <= bottom)


# 游戏循环渲染，一个线程重绘小球和障碍物
def main():
    clock = pygame.time.Clock()
    ball = Ball()
    obstacles = []
    running = True

    total_run_nums = 0
    while running:
        # 刷新频率不需要修改
        clock.tick(50)
        # 1秒一个障碍物，增加障碍物
        if total_run_nums % 10 == 0:  # 降低障碍物的生成频率
            obstacles.append(Obstacle())

        total_run_nums +=1
        window.fill(WHITE)

        # 处理事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 计算安全地图
        safe_map = generate_safe_map(ball, obstacles)
        # 应用腐蚀算法，去除狭长区域
        eroded_safe_map = apply_erosion(safe_map, structure_size=2)

        draw_safe_map(eroded_safe_map, window)

        # 找到最大安全区域的目标点
        safe_target = find_largest_safe_zone(eroded_safe_map)
        print(f"球可达的最佳安全区域目标点: {safe_target}")

        ball.move_towards(safe_target)

        # 移动障碍物
        for obstacle in obstacles:
            obstacle.fall()
            obstacle.draw(window)
            # 检测碰撞，球的圆心坐标在小木块内，包括边沿接触
            if is_colliding(ball, obstacle):
                print(f"Game Over! Your score is: {len(obstacles)}")
                running = False

        #绘制得分到屏幕上
        # 定义文本
        if running:
            text = 'Your score: %d' % len(obstacles)
        else:
            text = 'GameOver,Your score: %d' % len(obstacles)

        font = pygame.font.SysFont("SimHei", 30)
        # 准备渲染文本
        surface = font.render(text, True, (255, 108, 10))
        window.blit(surface, (20, 20))
        ball.draw(window)
        pygame.display.flip()

    # 处理事件
    done = False
    while not done:
        event = pygame.event.wait()
        if event.type == pygame.QUIT:
            done = True
    # 退出PyGame
    pygame.quit()


if __name__ == "__main__":
    main()