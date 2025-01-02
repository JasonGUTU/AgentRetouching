import os
from typing import List, Callable
import numpy as np
import cv2
from PIL import Image, ImageEnhance


# ============================================================================
# 亮度调整相关函数
# 包括:
# - black(): 调整暗部 (类似 Lightroom 的 Blacks)
# - white(): 调整亮部 (类似 Lightroom 的 Whites) 
# - tone(): 调整中间调 (类似 Lightroom 的 Exposure)
# ============================================================================


def exposure(input_image_path: str, output_image_path: str, exposure_factor: float):
    """
    @2024/10/27
    Adjust the exposure of the image.
    -- input_image_path: str, the path of the input image.
    -- output_image_path: str, the path of the output image.
    -- exposure_factor: float, the factor to adjust the exposure. [-5, 5]
    """
    with Image.open(input_image_path) as img:
        # Convert to NumPy array
        img_np = np.array(img)
        gamma = 1.0 / (1.0 + exposure_factor) if exposure_factor >= 0 else 1.0 - exposure_factor

        gamma_table = [np.power(x / 255.0, gamma) * 255.0 for x in range(256)]
        gamma_table = np.round(np.array(gamma_table)).astype(np.uint8)
        adjusted_img = cv2.LUT(img_np, gamma_table)

        adjusted_img = Image.fromarray(adjusted_img)
        
        adjusted_img.save(output_image_path)
        print(output_image_path)


def contrast(input_image_path: str, output_image_path: str, contrast_factor: float):  # checked 2025/01/02
    """
    模拟类似 Lightroom 的“对比度”调整 (示例级，不是官方算法)，
    在 Lab 空间里对 L 通道做 S 型曲线映射。

    参数:
        input_image_path (str): 输入图像 (可为 .npy 或常见 8 位/16 位格式)
        output_image_path (str): 输出图像 (同上)
        contrast_factor (float): 对比度调整因子, 范围 -100 ~ 100
            * >0 => 增强对比度
            * <0 => 减弱对比度

    返回:
        (np.ndarray) 调整后的图像, float32, [0,1], RGB
    """

    # 0) 规范化 contrast_factor => [-1,1]
    #    一般我们将用户输入[-100,100]映射到[-1,1]做内部运算
    contrast_intensity = np.clip(contrast_factor / 100.0, -1.0, 1.0)

    # 1) 读取并转换到 float32 [0,1], RGB
    ext_in = os.path.splitext(input_image_path)[-1].lower()

    if ext_in == '.npy':
        img = np.load(input_image_path)
        if img.ndim == 2:
            img = np.stack([img, img, img], axis=-1)
        elif img.shape[-1] == 4:
            img = img[..., :3]
        
        if img.dtype not in [np.float32, np.float64]:
            raise ValueError(".npy 图像应当是 float32/64。")

        img = img.astype(np.float32)
        bit_depth_in = 16  # 假设 .npy 来自高精度
    else:
        img_bgr = cv2.imread(input_image_path, cv2.IMREAD_UNCHANGED)

        if img_bgr.dtype == np.uint8:
            bit_depth_in = 8
            img = (img_bgr.astype(np.float32) / 255.0)
        elif img_bgr.dtype == np.uint16:
            bit_depth_in = 16
            img = (img_bgr.astype(np.float32) / 65535.0)
        else:
            raise ValueError("暂不支持此类型的位深")

        img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    # 2) 转到 Lab 空间 => L ∈ [0,100]
    lab = cv2.cvtColor(img.astype(np.float32), cv2.COLOR_RGB2LAB)

    L = lab[..., 0]  # [0,100]
    A = lab[..., 1]
    B = lab[..., 2]

    # 归一到 [0,1], 便于做曲线
    L_norm = L / 100.0

    # 3) 对比度映射 (S 曲线)
    def s_curve_contrast(L_channel: np.ndarray, c: float) -> np.ndarray:
        """
        S 型对比度曲线示例:
        L_out = 0.5 + tanh( alpha * (L_in - 0.5) ) * 0.5
        alpha = 1 + c * K
        c: [-1,1], c>0 => 增强对比, c<0 => 减弱对比
        K: 一个常数, 控制对比度响应强度
        """
        # 中心点 0.5 保持不变
        # alpha 决定曲线陡峭程度
        # c>0 => 越大越陡峭 => 对比更强
        # c<0 => 越小越平 => 对比更弱
        K = 1.0  # 你可以调大/调小该常数，增减曲线响应
        alpha = 1.0 + c * K

        # (L_in - 0.5) => 偏离中心
        # tanh(...) => S 型
        # 后面 * 0.5 + 0.5 => 映射回 [0,1] 大致区间
        out = 0.5 + np.tanh(alpha * (L_channel - 0.5)) * 0.5
        return out

    L_norm_adjusted = s_curve_contrast(L_norm, contrast_intensity)

    # clip到[0,1]以防数值越界
    L_norm_adjusted = np.clip(L_norm_adjusted, 0.0, 1.0)

    # 4) 拼回 Lab => 转回 RGB
    L_adjusted = (L_norm_adjusted * 100.0).astype(np.float32)
    lab_adjusted = np.stack([L_adjusted, A, B], axis=-1).astype(np.float32)
    img_contrast = cv2.cvtColor(lab_adjusted, cv2.COLOR_LAB2RGB)

    # 5) 保存结果
    ext_out = os.path.splitext(output_image_path)[-1].lower()

    if ext_out == '.npy':
        np.save(output_image_path, img_contrast)
    else:
        img_contrast = np.clip(img_contrast, 0.0, 1.0)
        if bit_depth_in == 8:
            out_8u = (img_contrast * 255.0).round().astype(np.uint8)
            cv2.imwrite(output_image_path, cv2.cvtColor(out_8u, cv2.COLOR_RGB2BGR))
        else:
            out_16u = (img_contrast * 65535.0).round().astype(np.uint16)
            cv2.imwrite(output_image_path, cv2.cvtColor(out_16u, cv2.COLOR_RGB2BGR))


def shadow(input_image_path: str, output_image_path: str, shadows_factor: float):  # checked 2025/01/02
    """
    调整图像的“阴影”部分（类似 Lightroom 中的 Shadows），全程 float 运算。
    大体沿用 black 函数的逻辑，只在关键处做最小改动。
    
    参数:
        input_image_path (str): 输入路径（.npy / 8 位 / 16 位）
        output_image_path (str): 输出路径（.npy / 8 位 / 16 位）
        shadows_factor (float): 阴影调整因子，-100~100
    """
    # ------------------ 0) 解析 shadows_factor => [-1, 1] ------------------
    intensity = np.clip(shadows_factor / 100.0, -1.0, 1.0)

    # ------------------ 1) 读取图像, 转为 float32 [0,1], RGB ---------------
    ext_in = os.path.splitext(input_image_path)[-1].lower()

    if ext_in == '.npy':
        img = np.load(input_image_path)
        if img.ndim == 2:
            img = np.stack([img, img, img], axis=-1)
        elif img.shape[-1] == 4:
            img = img[..., :3]

        if img.dtype not in [np.float32, np.float64]:
            raise ValueError(".npy 图像应当是 float32/64。")

        img = img.astype(np.float32)
        bit_depth_in = 16  
    else:
        img_bgr = cv2.imread(input_image_path, cv2.IMREAD_UNCHANGED)
        if img_bgr.dtype == np.uint8:
            bit_depth_in = 8
            img = img_bgr.astype(np.float32) / 255.0
        elif img_bgr.dtype == np.uint16:
            bit_depth_in = 16
            img = img_bgr.astype(np.float32) / 65535.0
        else:
            raise ValueError("仅支持 8 位 或 16 位图像。")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # ------------------ 2) 转到 float32 Lab => [L ∈ (0,100)] ---------------
    lab_f32 = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    L = lab_f32[..., 0]
    A = lab_f32[..., 1]
    B = lab_f32[..., 2]

    # 归一化 L => [0,1]
    L_norm = L / 100.0

    # ------------------ 3) Shadows 调整函数 (对比黑场稍更宽) ---------------
    def shadows_tone_mapping(L_channel: np.ndarray, factor: float) -> np.ndarray:
        """
        使用 S 形曲线来调整阴影：
        - factor > 0 => 压暗阴影
        - factor < 0 => 提亮阴影
        - factor = 0 => 原样返回

        下面使用了两个内部参数：
        - shadow_threshold: 阴影阈值，决定分界点（越大则“阴影”范围越宽）
        - shadow_compress: 压缩系数，避免提升或压暗过度
        """
        # 你可以根据需要调节这两个参数
        shadow_threshold = 0.4   # [0,1]，越大则阴影范围越宽
        shadow_compress  = 0.5   # [0,1]，越大则压缩越明显
        
        # 如果不需要调整，直接返回原 L
        if abs(factor) < 1e-8:
            return L_channel

        # 结果数组
        L_out = np.copy(L_channel)
        
        # 正负标记: factor > 0 => 压暗, factor < 0 => 提亮
        sign = np.sign(factor)   
        # 取绝对值做强度
        strength = abs(factor)

        # 遍历像素
        it = np.nditer(L_channel, flags=['multi_index'])
        while not it.finished:
            idx = it.multi_index
            x = L_channel[idx]  # L ∈ [0,1]
            
            if x < shadow_threshold:
                # 1) 计算归一化 t ∈ [0,1]
                t = x / shadow_threshold
                
                # 2) 计算基础提升/压暗量 (1 - t^2) 
                #    t=0 => 最大, t=1 => 0
                base = strength * (1.0 - t * t)

                # 3) 压缩系数
                #    shadow_compress 越大 => 越强的“抑制”作用
                #    c 在 t=1 时 = 1 => 不再抑制
                #    c 在 t=0 时 = 1 - compress => 最大抑制
                if shadow_compress > 0.0:
                    c = 1.0 - shadow_compress * (1.0 - t)
                    base *= c

                # 4) 根据正负来决定加/减
                if sign > 0:  
                    # factor>0 => 压暗 => 用 (1 - base)
                    y = x * (1.0 - base)
                else:
                    # factor<0 => 提亮 => 用 (1 + base)
                    y = x * (1.0 + base)

                L_out[idx] = y
            else:
                # 非阴影区域保持不变
                L_out[idx] = x
            
            it.iternext()

        return L_out

    # 调用
    L_norm_adjusted = shadows_tone_mapping(L_norm, intensity)
    L_norm_adjusted = np.clip(L_norm_adjusted, 0.0, 1.0)

    # ------------------ 4) 拼回 Lab => 转回 RGB [0,1] ----------------------
    L_adjusted = L_norm_adjusted * 100.0
    lab_adjusted = np.stack([L_adjusted, A, B], axis=-1)
    img_adjusted = cv2.cvtColor(lab_adjusted.astype(np.float32), cv2.COLOR_LAB2RGB)

    # ------------------ 5) 保存与返回 --------------------------------------
    ext_out = os.path.splitext(output_image_path)[-1].lower()

    if ext_out == '.npy':
        np.save(output_image_path, img_adjusted)
    else:
        img_adjusted = np.clip(img_adjusted, 0.0, 1.0)
        if bit_depth_in == 8:
            out_8u = (img_adjusted * 255.0).round().astype(np.uint8)
            cv2.imwrite(output_image_path, cv2.cvtColor(out_8u, cv2.COLOR_RGB2BGR))
        else:
            out_16u = (img_adjusted * 65535.0).round().astype(np.uint16)
            cv2.imwrite(output_image_path, cv2.cvtColor(out_16u, cv2.COLOR_RGB2BGR))


def highlight(input_image_path: str, output_image_path: str, highlights_factor: float):  # checked 2025/01/02
    """
    调整图像的“高光”部分（类似 Lightroom 中的 Highlights），全程 float 运算。
    大体沿用 black/shadow 函数的结构，只在关键处做最小改动。

    参数:
        input_image_path (str): 输入路径（.npy / 8 位 / 16 位）
        output_image_path (str): 输出路径（.npy / 8 位 / 16 位）
        highlights_factor (float): 高光调整因子，-100~100
            >0 => 提升高光；<0 => 压暗高光

    返回:
        img_adjusted (np.ndarray): 调整后的图像(float32, [0,1], RGB)
    """
    # ------------------ 0) 解析 highlights_factor => [-1,1] ------------------
    intensity = np.clip(highlights_factor / 100.0, -1.0, 1.0)

    # ------------------ 1) 读取图像, 转为 float32 [0,1], RGB ---------------
    ext_in = os.path.splitext(input_image_path)[-1].lower()

    if ext_in == '.npy':
        img = np.load(input_image_path)
        if img.ndim == 2:
            # 单通道 => 扩为3通道
            img = np.stack([img, img, img], axis=-1)
        elif img.shape[-1] == 4:
            # 有 alpha 通道 => 取前三通道
            img = img[..., :3]

        if img.dtype not in [np.float32, np.float64]:
            raise ValueError(".npy 图像应当是 float32/64。")
        img = img.astype(np.float32)
        bit_depth_in = 16  
    else:
        # OpenCV 读图 => BGR
        img_bgr = cv2.imread(input_image_path, cv2.IMREAD_UNCHANGED)
        if img_bgr is None:
            raise IOError(f"无法读取图像: {input_image_path}")

        if img_bgr.dtype == np.uint8:
            bit_depth_in = 8
            img = img_bgr.astype(np.float32) / 255.0
        elif img_bgr.dtype == np.uint16:
            bit_depth_in = 16
            img = img_bgr.astype(np.float32) / 65535.0
        else:
            raise ValueError("仅支持 8 位 或 16 位图像。")

        # BGR -> RGB
        img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    # ------------------ 2) 转到 float32 Lab => L ∈ [0,100] ------------------
    lab_f32 = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    L = lab_f32[..., 0]  # [0,100]
    A = lab_f32[..., 1]
    B = lab_f32[..., 2]

    # 归一到 [0,1]
    L_norm = L / 100.0

    # ------------------ 3) Highlights 调整函数 -------------------------------
    def highlights_tone_mapping(L_channel: np.ndarray, factor: float) -> np.ndarray:
        """
        针对较亮区间做调整:
          factor: [-1,1]，>0 => 提亮高光, <0 => 压暗高光
        """
        # 对比 black/shadow，这里我们用一个对“亮部”更敏感的权重:
        #   weight = L^3 或 L^4 (示例：L^3)
        # 这样当 L>0.6~0.7 时，权重开始变得比较大；中低亮度则较小。
        weight = np.power(L_channel, 4.0)

        if factor > 0:
            # 提升高光 => 用对数+小系数
            # 跟 black/shadow 类似，但可改小/改大系数看需求
            adjustment = weight * factor * np.log1p(L_channel) * 0.2
        elif factor < 0:
            # 压暗高光 => 用 exp(...) 让接近1的区域衰减
            adjustment = weight * factor * np.exp(-(1 - L_channel)*2.5) * 0.5
        else:
            adjustment = 0

        return L_channel + adjustment

    # 调用
    L_norm_adjusted = highlights_tone_mapping(L_norm, intensity)
    L_norm_adjusted = np.clip(L_norm_adjusted, 0.0, 1.0)

    # ------------------ 4) 拼回 Lab => 转回 RGB [0,1] ----------------------
    L_adjusted = L_norm_adjusted * 100.0
    lab_adjusted = np.stack([L_adjusted, A, B], axis=-1).astype(np.float32)
    img_adjusted = cv2.cvtColor(lab_adjusted, cv2.COLOR_LAB2RGB)

    # ------------------ 5) 保存&返回 ---------------------------------------
    ext_out = os.path.splitext(output_image_path)[-1].lower()

    if ext_out == '.npy':
        np.save(output_image_path, img_adjusted)
    else:
        img_adjusted = np.clip(img_adjusted, 0, 1)
        if bit_depth_in == 8:
            out_8u = (img_adjusted * 255.0).round().astype(np.uint8)
            cv2.imwrite(output_image_path, cv2.cvtColor(out_8u, cv2.COLOR_RGB2BGR))
        else:
            out_16u = (img_adjusted * 65535.0).round().astype(np.uint16)
            cv2.imwrite(output_image_path, cv2.cvtColor(out_16u, cv2.COLOR_RGB2BGR))


def black(input_image_path: str, output_image_path: str, blacks_factor: float):  # Checked 2025/01/02
    """
    调整图像的黑色色阶（类似 Lightroom 的 Blacks 调整，非完全一致）
    保留全程 float 运算，以尽量保持 16 位精度。
    
    参数：
        input_image_path (str): 输入图像的路径（.npy / 8 位 / 16 位）
        output_image_path (str): 输出图像的保存路径（.npy / 通常 8 或 16 位）
        blacks_factor (float): 黑色色阶调整因子，范围为 -100 到 100
        
    返回：
        img_rgb (np.ndarray): 调整后的图像（float32，范围 [0,1]，RGB）
    """
    # ------------------------------------------------------------------------
    # 0) 解析 blacks_factor 到 [-1, 1]
    # ------------------------------------------------------------------------
    intensity = np.clip(blacks_factor / 100.0, -1.0, 1.0)

    # ------------------------------------------------------------------------
    # 1) 读取图像到 img(float32, [0,1], RGB)
    # ------------------------------------------------------------------------
    ext_in = os.path.splitext(input_image_path)[-1].lower()

    if ext_in == '.npy':
        # 视为已经是 [0,1] 的 float32/64，通道顺序 RGB
        img = np.load(input_image_path)
        if img.ndim == 2:
            # 单通道 => 扩为3通道
            img = np.stack([img, img, img], axis=-1)
        elif img.shape[-1] == 4:
            # 如果有 alpha 通道 => 截到3通道
            img = img[..., :3]

        if img.dtype not in [np.float32, np.float64]:
            raise ValueError(".npy 图像应当是 float32/64。")
        img = img.astype(np.float32)

        # 对于 npy，默认视为高精度 => bit_depth_in = 16
        bit_depth_in = 16  
    else:
        # 用 OpenCV 读取 => BGR
        img_bgr = cv2.imread(input_image_path, cv2.IMREAD_UNCHANGED)

        # 判断是 8 位 还是 16 位
        if img_bgr.dtype == np.uint8:
            bit_depth_in = 8
            img = img_bgr.astype(np.float32) / 255.0
        elif img_bgr.dtype == np.uint16:
            bit_depth_in = 16
            img = img_bgr.astype(np.float32) / 65535.0
        else:
            raise ValueError("仅支持 8 位 或 16 位图像。")

        # 转成 RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # ------------------------------------------------------------------------
    # 2) 使用 cv2 的浮点 Lab 转换 => L 范围 [0,100], a/b 大约 [-128, 127]
    #    (OpenCV 会假定输入是 [0,1]，输出 L 通道就是 [0,100])
    # ------------------------------------------------------------------------
    # 注意：OpenCV 对 float32 的 RGB2LAB 会自动假定 sRGB+D65 等。
    #       结果中 L 通道为 [0, 100]，a/b 大约 [-128, 127]
    lab_f32 = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)  # float32

    # 拆分通道
    L = lab_f32[..., 0]  # [0,100]
    A = lab_f32[..., 1]  # [-128,127]
    B = lab_f32[..., 2]  # [-128,127]

    # 归一化 L 到 [0,1] 以便做 blacks 映射
    L_norm = L / 100.0

    # ------------------------------------------------------------------------
    # 3) Blacks 调整函数
    # ------------------------------------------------------------------------
    def blacks_tone_mapping(L_channel: np.ndarray, blacks_intensity: float) -> np.ndarray:
        """
        L_channel: [0,1]
        blacks_intensity: [-1,1]
        """
        # 暗部权重
        weight = np.power(np.abs(1 - L_channel), 8.0)

        if blacks_intensity > 0:
            # blacks_intensity > 0 => 压暗
            adjustment = weight * blacks_intensity * np.log1p(1 - L_channel) * 0.5
        elif blacks_intensity < 0:
            # blacks_intensity < 0 => 提亮暗部
            adjustment = weight * blacks_intensity * np.exp(-L_channel * 3) * 0.6
        else:
            adjustment = 0

        return L_channel + adjustment

    L_norm_adjusted = blacks_tone_mapping(L_norm, intensity)
    L_norm_adjusted = np.clip(L_norm_adjusted, 0.0, 1.0)

    # ------------------------------------------------------------------------
    # 4) 拼回 Lab，转换回 RGB
    # ------------------------------------------------------------------------
    # 先把 L_norm_adjusted 映射回 [0,100]
    L_adjusted = L_norm_adjusted * 100.0

    lab_adjusted = np.stack([L_adjusted, A, B], axis=-1)
    # 这里 lab_adjusted 依旧是 float32
    # 再做 LAB2RGB => 得到 float32 => RGB, 范围 [0,1]
    img_adjusted = cv2.cvtColor(lab_adjusted.astype(np.float32), cv2.COLOR_LAB2RGB)

    # ------------------------------------------------------------------------
    # 5) 保存并返回
    # ------------------------------------------------------------------------
    ext_out = os.path.splitext(output_image_path)[-1].lower()

    if ext_out == '.npy':
        # 直接保存 [0,1] float32
        np.save(output_image_path, img_adjusted)
    else:
        img_adjusted = np.clip(img_adjusted, 0.0, 1.0)
        # 根据输入图像位深选择输出。你也可以自定义。
        if bit_depth_in == 8:
            # 输出 8 位
            out_8u = (img_adjusted * 255.0).round().astype(np.uint8)
            cv2.imwrite(output_image_path, cv2.cvtColor(out_8u, cv2.COLOR_RGB2BGR))
        else:
            # 输出 16 位
            out_16u = (img_adjusted * 65535.0).round().astype(np.uint16)

            cv2.imwrite(output_image_path, cv2.cvtColor(out_16u, cv2.COLOR_RGB2BGR))


def white(input_image_path: str, output_image_path: str, whites_factor: float):  # Checked 2025/01/02
    """
    调整图像的白色色阶（类似 Lightroom 的 Whites 调整，非完全一致）
    保留全程 float 运算，以尽量保持 16 位精度。
    
    参数：
        input_image_path (str): 输入图像的路径（.npy / 8 位 / 16 位）
        output_image_path (str): 输出图像的保存路径（.npy / 通常 8 或 16 位）
        whites_factor (float): 白色色阶调整因子，范围为 -100 到 100
    """
    # ------------------------------------------------------------------------
    # 0) 将用户输入的 [-100, 100] 范围映射到 [-1, 1]
    # ------------------------------------------------------------------------
    intensity = np.clip(whites_factor / 100.0, -1.0, 1.0)

    # ------------------------------------------------------------------------
    # 1) 读取图像到 img(float32, [0,1], RGB)
    # ------------------------------------------------------------------------
    ext_in = os.path.splitext(input_image_path)[-1].lower()

    if ext_in == '.npy':
        # 视为已经是 [0,1] 的 float32/64，通道顺序 RGB
        img = np.load(input_image_path)
        if img.ndim == 2:
            # 单通道 => 扩为3通道
            img = np.stack([img, img, img], axis=-1)
        elif img.shape[-1] == 4:
            # 如果有 alpha 通道 => 截到3通道
            img = img[..., :3]

        if img.dtype not in [np.float32, np.float64]:
            raise ValueError(".npy 图像应当是 float32/64。")
        img = img.astype(np.float32)

        # 对于 npy，默认视为高精度 => bit_depth_in = 16
        bit_depth_in = 16  
    else:
        # 用 OpenCV 读取 => BGR
        img_bgr = cv2.imread(input_image_path, cv2.IMREAD_UNCHANGED)

        # 判断是 8 位 还是 16 位
        if img_bgr.dtype == np.uint8:
            bit_depth_in = 8
            img = img_bgr.astype(np.float32) / 255.0
        elif img_bgr.dtype == np.uint16:
            bit_depth_in = 16
            img = img_bgr.astype(np.float32) / 65535.0
        else:
            raise ValueError("仅支持 8 位 或 16 位图像。")

        # 转成 RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # ------------------------------------------------------------------------
    # 2) 使用 cv2 的浮点 Lab 转换 => L 范围 [0,100], a/b 大约 [-128, 127]
    #    (OpenCV 会假定输入是 [0,1]，输出 L 通道就是 [0,100])
    # ------------------------------------------------------------------------
    # 注意：OpenCV 对 float32 的 RGB2LAB 会自动假定 sRGB+D65 等。
    #       结果中 L 通道为 [0, 100]，a/b 大约 [-128, 127]
    lab_f32 = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)  # float32

    # 拆分通道
    L = lab_f32[..., 0]  # [0,100]
    A = lab_f32[..., 1]  # [-128,127]
    B = lab_f32[..., 2]  # [-128,127]

    # 归一化 L 到 [0,1] 以便做 blacks 映射
    L_norm = L / 100.0

    # ------------------------------------------------------------------------
    # 3) Whites 调整函数
    #    思路：对于更亮的区域，给更高的权重，从而更显著地提升/压低高光
    # ------------------------------------------------------------------------
    def whites_tone_mapping(L_channel: np.ndarray, white_intensity: float) -> np.ndarray:
        """
        L_channel: [0,1]
        white_intensity: [-1,1]
        """
        # 我们用 sqrt(L) 作为权重 => L 越大 => sqrt(L) 越大 => 亮部影响更大
        weight = np.power(L_channel, 11.0)

        if white_intensity > 0:
            # white_intensity > 0 => 提升亮部 => 让亮的更亮
            # 用对数做一些柔和映射
            adjustment = weight * white_intensity * np.log1p(L_channel) * 0.15
        elif white_intensity < 0:
            # white_intensity < 0 => 压低亮部 => 减少过曝
            # 用 exp(...) 让接近 1 的地方衰减更明显
            adjustment = weight * white_intensity * np.exp(- (1 - L_channel) * 3) * 0.4
        else:
            adjustment = 0.0

        return L_channel + adjustment

    L_norm_adjusted = whites_tone_mapping(L_norm, intensity)
    L_norm_adjusted = np.clip(L_norm_adjusted, 0.0, 1.0)

    # ------------------------------------------------------------------------
    # 4) 组合回 Lab => 转回 RGB
    # ------------------------------------------------------------------------
    L_adjusted = L_norm_adjusted * 100.0
    lab_adjusted = np.stack([L_adjusted, A, B], axis=-1)
    # 转回 RGB [0,1]
    img_adjusted = cv2.cvtColor(lab_adjusted.astype(np.float32), cv2.COLOR_LAB2RGB)

    # ------------------------------------------------------------------------
    # 5) 保存 & 返回
    # ------------------------------------------------------------------------
    ext_out = os.path.splitext(output_image_path)[-1].lower()

    if ext_out == '.npy':
        # 保存为 float32 [.npy], [0,1], RGB
        np.save(output_image_path, img_adjusted)
    else:
        img_adjusted = np.clip(img_adjusted, 0.0, 1.0)
        if bit_depth_in == 8:
            # 输出 8 位
            out_8u = (img_adjusted * 255.0).round().astype(np.uint8)
            cv2.imwrite(output_image_path, cv2.cvtColor(out_8u, cv2.COLOR_RGB2BGR))
        else:
            # 输出 16 位
            out_16u = (img_adjusted * 65535.0).round().astype(np.uint16)
            cv2.imwrite(output_image_path, cv2.cvtColor(out_16u, cv2.COLOR_RGB2BGR))


# ============================================================================
# 色彩调整相关函数
# 包括:
# - saturation(): 调整饱和度 (类似 Lightroom 的 Saturation)
# - color_temperature(): 调整色温 (类似 Lightroom 的 Temperature)
# - contrast(): 调整对比度 (类似 Lightroom 的 Contrast)
# ============================================================================


def saturation(input_image_path: str, output_image_path: str, saturation_factor: float):  # Checked 2025/01/01
    """
    Adjust the saturation of an image using the HSL color model.

    Parameters:
        input_image_path (str): Path to the input image.
        output_image_path (str): Path to save the adjusted image.
        saturation_factor (float): Saturation adjustment factor in the range [-100, 100].
                                   - -100: Completely desaturate (gray image).
                                   - 0: No change.
                                   - 100: Saturation increased to double.
    
    Returns:
        None: The adjusted image is saved to the output_image_path.
    """
    # Ensure saturation_factor is within the valid range
    saturation_factor = np.clip(saturation_factor, -100, 100)

    # Map saturation_factor (-100 to 100) to a scaling factor (0.0 to 2.0)
    scale_factor = 1 + saturation_factor / 100.0

    if input_image_path.endswith(".npy"):
        img = np.load(input_image_path)
    else:
        # Load the input image
        img_raw = cv2.imread(input_image_path, cv2.IMREAD_UNCHANGED)
        if img_raw is None:
            raise FileNotFoundError(f"Image not found at path: {input_image_path}")
    
        if img_raw.dtype == np.uint8:
            max_pixel_value = 255.0
        elif img_raw.dtype == np.uint16:
            max_pixel_value = 65535.0
        else:
            raise ValueError(f"Unsupported image type: {img_raw.dtype}")
        # Convert BGR to RGB for processing
        img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB).astype(np.float32) / max_pixel_value  # Normalize to [0, 1]

    # Step 1: Convert RGB to HSL
    def rgb_to_hsl(image):
        """Convert RGB image to HSL color space."""
        r, g, b = image[..., 0], image[..., 1], image[..., 2]
        max_val = np.max(image, axis=-1)
        min_val = np.min(image, axis=-1)
        l = (max_val + min_val) / 2

        delta = max_val - min_val
        s = np.zeros_like(l)
        h = np.zeros_like(l)

        # Saturation calculation
        mask = delta > 0
        s[mask & (l < 0.5)] = delta[mask & (l < 0.5)] / (max_val[mask & (l < 0.5)] + min_val[mask & (l < 0.5)])
        s[mask & (l >= 0.5)] = delta[mask & (l >= 0.5)] / (2 - max_val[mask & (l >= 0.5)] - min_val[mask & (l >= 0.5)])

        # Hue calculation
        mask_r = (max_val == r) & mask
        mask_g = (max_val == g) & mask
        mask_b = (max_val == b) & mask

        h[mask_r] = ((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6
        h[mask_g] = ((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2
        h[mask_b] = ((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4

        h /= 6
        h[h < 0] += 1  # Ensure hue is in [0, 1]

        return h, s, l

    # Step 2: Adjust the saturation
    def adjust_hsl_saturation(h, s, l, scale_factor):
        """Adjust the saturation in HSL space."""
        s = np.clip(s * scale_factor, 0, 1)  # Scale the saturation by the factor
        return h, s, l

    # Step 3: Convert HSL back to RGB
    def hsl_to_rgb(h, s, l):
        """Convert HSL image back to RGB color space."""
        c = (1 - np.abs(2 * l - 1)) * s
        x = c * (1 - np.abs((h * 6) % 2 - 1))
        m = l - c / 2

        rgb = np.zeros((h.shape[0], h.shape[1], 3), dtype=np.float32)
        h6 = h * 6

        idx = (h6 < 1)
        rgb[idx] = np.stack([c[idx], x[idx], np.zeros_like(c[idx])], axis=-1)

        idx = (1 <= h6) & (h6 < 2)
        rgb[idx] = np.stack([x[idx], c[idx], np.zeros_like(c[idx])], axis=-1)

        idx = (2 <= h6) & (h6 < 3)
        rgb[idx] = np.stack([np.zeros_like(c[idx]), c[idx], x[idx]], axis=-1)

        idx = (3 <= h6) & (h6 < 4)
        rgb[idx] = np.stack([np.zeros_like(c[idx]), x[idx], c[idx]], axis=-1)

        idx = (4 <= h6) & (h6 < 5)
        rgb[idx] = np.stack([x[idx], np.zeros_like(c[idx]), c[idx]], axis=-1)

        idx = (5 <= h6) & (h6 < 6)
        rgb[idx] = np.stack([c[idx], np.zeros_like(c[idx]), x[idx]], axis=-1)

        return np.clip(rgb + m[..., None], 0, 1)

    # Convert RGB to HSL
    h, s, l = rgb_to_hsl(img)

    # Adjust the saturation
    h, s, l = adjust_hsl_saturation(h, s, l, scale_factor)

    # Convert HSL back to RGB
    adjusted_img = hsl_to_rgb(h, s, l)

    if input_image_path.endswith(".npy"):
        np.save(output_image_path, adjusted_img)
        print(f"Saturation adjusted image npy saved to {output_image_path}")
    else:
        # Convert back to 8-bit format
        final_image = (adjusted_img * max_pixel_value).astype(img_raw.dtype)

        bgr_final_image = cv2.cvtColor(final_image, cv2.COLOR_RGB2BGR)
        # 保存为 TIFF
        cv2.imwrite(output_image_path, bgr_final_image)
        print(f"Saturation adjusted image saved to {output_image_path}")


def tone(input_image_path: str, output_image_path: str, tone_factor: float):
    """
    @2024/10/27
    Adjust the tone of the image.
    -- input_image_path: str, the path of the input image.
    -- output_image_path: str, the path of the output image.
    -- tone_factor: float, the factor to adjust the tone. [-150, 150]
    """
    img_raw = cv2.imread(input_image_path)
    value = -1 * tone_factor
    b, g, r = cv2.split(img_raw)
    
    if value >= 0:
        lim = 255 - value
        g[g > lim] = 255
        g[g <= lim] += value
      
    else:
        lim = 0 - value
        g[g < lim] = 0
        g[g >= lim] -= abs(value)

    
    image = cv2.merge((b, g, r))
    img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    output_image = Image.fromarray(img)
    output_image.save(output_image_path)
    print(output_image_path)


def color_temperature(input_image_path: str, output_image_path: str, color_temperature_factor: float):
    """
    @2024/10/27
    Adjust the color temperature of the image.
    -- input_image_path: str, the path of the input image.
    -- output_image_path: str, the path of the output image.
    -- color_temperature_factor: float, the factor to adjust the color temperature. [2000, 50000]
    !! We set the original color temperature to 6000K.
    """
    img_raw = cv2.imread(input_image_path)
    img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2RGB)
    original_temp = 6000
    value = np.clip(color_temperature_factor, 2000, 50000)  # Ensure value is within the specified range
    if value > original_temp:
        value = ((value - original_temp) / (50000 - original_temp)) * 100  # Map to 0-100
    else:
        value = ((value - original_temp) / (original_temp - 2000)) * 100  # Map to -100-0
    print(value)
    value = np.round(value)  # Convert to uint8 to avoid casting issues
    b, g, r = cv2.split(img)
    value = int(-1 * value)
    print(value)
    if value >= 0:
        lim = 255 - value
        r[r > lim] = 255
        r[r <= lim] += value
        
        lim1 = 0 + value
        b[b < lim1] = 0
        b[b >= lim1] -= value
        
    else:
        lim = 0 - value
        r[r < lim] = 0
        r[r >= lim] -= abs(value)
        
        lim = 255 - abs(value)
        b[b > lim] = 255
        b[b <= lim] += abs(value)

    image = cv2.merge((b, g, r))
    #image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Convert to RGB before saving
    output_image = Image.fromarray(image)
    output_image.save(output_image_path)
    print(output_image_path)


if __name__ == "__main__":
    saturation("berowra-landscape-photography.jpg", "cache/test/000.jpg", 100)
    # shadows("berowra-landscape-photography.jpg", "cache/test/001.jpg", -100)
    highlights("berowra-landscape-photography.jpg", "cache/test/002.jpg", 100)
    contrast("berowra-landscape-photography.jpg", "cache/test/003.jpg", -100)
    black("berowra-landscape-photography.jpg", "cache/test/004.jpg", -40)
    white("berowra-landscape-photography.jpg", "cache/test/005.jpg", 100)
    tone("berowra-landscape-photography.jpg", "cache/test/006.jpg", 30)
    color_temperature("berowra-landscape-photography.jpg", "cache/test/007.jpg", 1000)
    exposure("berowra-landscape-photography.jpg", "cache/test/008.jpg", 1)