import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import matplotlib.pyplot as plt
from typing import List
from tqdm import tqdm


# 常量定义
BATCH_SIZE = 64
EPOCHS = 20
LEARNING_RATE = 0.01
MOMENTUM = 0.5
MNIST_MEAN = 0.1307
MNIST_STD = 0.3081


def get_device() -> str:
    """自动选择可用的计算设备"""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class InceptionBlock(nn.Module):
    """Inception模块实现"""
    def __init__(self, in_channels: int):
        super().__init__()
        
        # 1x1卷积分支
        self.branch1x1 = nn.Conv2d(in_channels, 16, kernel_size=1)
        
        # 5x5卷积分支
        self.branch5x5 = nn.Sequential(
            nn.Conv2d(in_channels, 16, kernel_size=1),
            nn.Conv2d(16, 24, kernel_size=5, padding=2)
        )
        
        # 3x3卷积分支
        self.branch3x3 = nn.Sequential(
            nn.Conv2d(in_channels, 16, kernel_size=1),
            nn.Conv2d(16, 24, kernel_size=3, padding=1),
            nn.Conv2d(24, 24, kernel_size=3, padding=1)
        )
        
        # 池化分支
        self.branch_pool = nn.Sequential(
            nn.AvgPool2d(kernel_size=3, stride=1, padding=1),
            nn.Conv2d(in_channels, 24, kernel_size=1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        branch1 = self.branch1x1(x)
        branch2 = self.branch5x5(x)
        branch3 = self.branch3x3(x)
        branch4 = self.branch_pool(x)
        
        # 沿通道维度拼接特征图
        return torch.cat([branch1, branch2, branch3, branch4], dim=1)


class MNISTNet(nn.Module):
    """MNIST分类网络结构"""
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 10, kernel_size=5)
        self.inception1 = InceptionBlock(in_channels=10)
        
        self.conv2 = nn.Conv2d(88, 20, kernel_size=5)  # 88 = 24*3 + 16
        self.inception2 = InceptionBlock(in_channels=20)
        
        self.maxpool = nn.MaxPool2d(2)
        self.fc = nn.Linear(1408, 10)  # 全连接层

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # 第一层卷积+池化+Inception
        x = self.maxpool(F.relu(self.conv1(x)))
        x = self.inception1(x)
        
        # 第二层卷积+池化+Inception
        x = self.maxpool(F.relu(self.conv2(x)))
        x = self.inception2(x)
        
        # 展平特征图并分类
        x = x.view(x.size(0), -1)
        return self.fc(x)


def load_data() -> tuple[DataLoader, DataLoader]:
    """加载MNIST数据集"""
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((MNIST_MEAN,), (MNIST_STD,))
    ])
    
    train_set = datasets.MNIST(
        root='./data/mnist/', 
        train=True, 
        download=True, 
        transform=transform
    )
    test_set = datasets.MNIST(
        root='./data/mnist/', 
        train=False, 
        download=True, 
        transform=transform
    )
    
    train_loader = DataLoader(
        train_set, 
        batch_size=BATCH_SIZE, 
        shuffle=True
    )
    test_loader = DataLoader(
        test_set, 
        batch_size=BATCH_SIZE, 
        shuffle=False
    )
    
    return train_loader, test_loader


def train_epoch(
    model: nn.Module, 
    loader: DataLoader, 
    optimizer: optim.Optimizer, 
    criterion: nn.Module,
    device: str,
    epoch: int
) -> None:
    """训练单个epoch"""
    model.train()
    running_loss = 0.0

    # 在训练循环外部创建进度条
    with tqdm(enumerate(loader), total=len(loader), desc=f'Epoch {epoch+1}', unit='batch') as pbar:
        for batch_idx, (inputs, targets) in pbar:
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
            # 实时更新进度条显示
            pbar.set_postfix({
                'loss': f'{loss.item():.3f}',
                'running_loss': f'{running_loss/(batch_idx+1):.3f}'
            })
            
            # 每300批次打印一次详细训练状态（可选）
            if batch_idx % 300 == 299:
                avg_loss = running_loss / 300
                pbar.write(f'Epoch [{epoch+1}], Batch [{batch_idx+1}]: Loss: {avg_loss:.3f}')
                running_loss = 0.0

def evaluate(
    model: nn.Module, 
    loader: DataLoader, 
    device: str
) -> float:
    """在测试集上评估模型"""
    model.eval()
    correct = 0
    total = 0
    
    with torch.no_grad():
        for inputs, targets in loader:
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = model(inputs)
            _, predicted = torch.max(outputs, dim=1)
            
            total += targets.size(0)
            correct += (predicted == targets).sum().item()
    
    accuracy = 100 * correct / total
    print(f'Test Accuracy: {accuracy:.2f}%')
    return accuracy


def plot_accuracy(accuracies: List[float]) -> None:
    """绘制准确率变化曲线"""
    plt.figure(figsize=(10, 5))
    plt.plot(accuracies, marker='o')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy (%)')
    plt.title('Test Accuracy vs. Epochs')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('mnist_accuracy.png')
    plt.show()


def main():
    # 设置计算设备
    device = get_device()
    print(f"Using device: {device}")
    
    # 加载数据
    train_loader, test_loader = load_data()
    
    # 初始化模型
    model = MNISTNet().to(device)
    
    # 定义损失函数和优化器
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(
        model.parameters(), 
        lr=LEARNING_RATE, 
        momentum=MOMENTUM
    )
    
    # 训练和评估循环
    accuracies = []
    for epoch in range(EPOCHS):
        train_epoch(model, train_loader, optimizer, criterion, device, epoch)
        accuracy = evaluate(model, test_loader, device)
        accuracies.append(accuracy)
    
    # 绘制准确率曲线
    plot_accuracy(accuracies)


if __name__ == '__main__':
    main()