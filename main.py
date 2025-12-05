"""
@author: lzx
@contact: bigdata_lzx@163.com
@time: 2025/11/28 下午6:21
@desc: FastAPI 服务入口模块，供 uvicorn 加载 app 实例。
"""
# ============================================================
# [Fix] 屏蔽 Paramiko < 3.0 产生的 CryptographyDeprecationWarning
# 必须放在任何 import app 之前执行，否则拦截无效
import warnings
try:
    from cryptography.utils import CryptographyDeprecationWarning
    warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
except ImportError:
    pass
# ============================================================

from app.main import app
import warnings
from cryptography.utils import CryptographyDeprecationWarning

# 这里原本的 filterwarnings 可以保留或删除，上面的代码已经生效了
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)

if __name__ == "__main__":
    import uvicorn
    # 注意：reload 模式下，部分警告可能会在重载时再次出现，属正常现象
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)