"""QuantLab 主入口

用法:
    python main.py --help                          显示帮助
    python main.py trading --help                   trading 子命令帮助
    python main.py trading --status --mode paper    查看账户状态
    python main.py trading --run-backtest data.csv  用CSV运行回测
"""
from quantlab.cli.main import main

if __name__ == "__main__":
    main()
