import matplotlib.pyplot as plt
import numpy as np

# Khởi tạo seed để kết quả cố định
np.random.seed(42)

fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True, sharey=True)
colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
titles = ["Environment $E_1$ (Clustered)", "Environment $E_2$ (Uniform)", "Environment $E_3$ (Mixed Noise)"]

# Tọa độ Depot cố định ở tâm
depot = np.array([50, 50])

for i, ax in enumerate(axes):
    ax.set_facecolor("#f8f9fa")
    ax.grid(True, linestyle="--", alpha=0.5, color="#ccc")

    # Vẽ Depot
    ax.scatter(depot[0], depot[1], color="#d62728", marker="s", s=150, zorder=5, label="Depot" if i == 0 else "")

    if i == 0:  # Clustered distribution
        # Tạo 3 cụm khách hàng ngẫu nhiên
        c1 = np.random.normal(loc=[25, 25], scale=7, size=(10, 2))
        c2 = np.random.normal(loc=[75, 75], scale=7, size=(10, 2))
        c3 = np.random.normal(loc=[30, 75], scale=8, size=(10, 2))
        customers = np.vstack([c1, c2, c3])
    elif i == 1:  # Uniform distribution
        customers = np.random.uniform(low=10, high=90, size=(30, 2))
    else:  # Mixed / Extracted Distribution with vary sizes
        c1 = np.random.normal(loc=[70, 30], scale=10, size=(15, 2))
        c2 = np.random.uniform(low=10, high=50, size=(15, 2))
        customers = np.vstack([c1, c2])

    # Giới hạn tọa độ trong khoảng [0, 100]
    customers = np.clip(customers, 0, 100)

    # Kích cỡ node đại diện cho Demand (q_i) biến đổi ngẫu nhiên ngụ ý Domain Randomization
    demands = np.random.randint(5, 25, size=len(customers))

    # Vẽ các node khách hàng
    scatter = ax.scatter(
        customers[:, 0],
        customers[:, 1],
        s=demands * 5,
        color=colors[i],
        alpha=0.8,
        edgecolors="black",
        linewidths=0.8,
        label="Randomized Customers" if i == 0 else "",
    )

    ax.set_title(titles[i], fontsize=14, fontweight="bold", pad=12, color="#333333")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    if i == 0:
        ax.set_ylabel("Y Coordinate", fontsize=12, fontweight="bold")
    ax.set_xlabel("X Coordinate", fontsize=12, fontweight="bold")

# Thêm chú thích tổng quát cho đồ thị đầu thiện
axes[0].legend(loc="upper left", frameon=True, facecolor="white", edgecolor="none")

plt.tight_layout()
# Lưu file chất lượng cao để nhét vào poster
plt.savefig("domain_randomization_vrp.png", dpi=300, bbox_inches="tight")
plt.show()
