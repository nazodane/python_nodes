# Copyright (c) 2026 Toshimitsu Kimura <lovesyao@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

bl_info = {
    "name": "Python Nodes",
    "author": "Toshimitsu Kimura",
    "description": "",
    "blender": (5, 1, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Generic",
}

# $ pip install fake-bpy-module pyrefly --break-system-packages
# $ code --install-extension ms-python.python ms-python.black-formatter ms-python.debugpy
# $ code --install-extension meta.pyrefly JacquesLucke.blender-development
# $ code --install-extension google.geminicodeassist

# TODO: njpwerner.autodocstring をテストする

from typing import TYPE_CHECKING
import bpy
from nodeitems_utils import NodeCategory, NodeItem

if TYPE_CHECKING:
    class NodeItem:
        # XXX: workaround the bug in fake-bpy-module
        def __init__(self, nodetype, *, label=None, settings=None, poll=None):
            ...

from nodeitems_utils import register_node_categories, unregister_node_categories

import ast

# =====================================================
# Node Tree
# =====================================================
class PythonNodeTree(bpy.types.NodeTree):
    bl_idname = "PythonNodeTree"
    bl_label = "Python Node Tree"
    bl_icon = "NODETREE"

    @classmethod
    def poll(cls, context):
        return True

# =====================================================
# Socket
# =====================================================
class PythonValueSocket(bpy.types.NodeSocket):
    bl_idname = "PythonValueSocket"
    bl_label = "Python Value"

    def draw(self, context, layout, node, text):
        layout.label(text=text)

    def draw_color(self, context, node):
        return (0.3, 0.6, 1.0, 1.0)

# =====================================================
# Node
# =====================================================
class PythonBaseNode(bpy.types.Node):
    """
    ベースクラス
    """

    depth: bpy.props.IntProperty(name="Depth", default=0) # type: ignore

    @classmethod
    def poll(cls, ntree):
        return ntree is not None and ntree.bl_idname == "PythonNodeTree"

#    def draw_label(self):
#        return "%s (%s)"%(self.bl_label, self.depth)

#    def update(self):
#       self.name = self.value

#    def insert_link(self, link: bpy.types.NodeLink):
#        if self == link.from_node:
#            return
#
#        self.update_depth(link.from_node.depth + 1)

    def update(self):
        depth = 0
        for inputs in self.inputs:
            for link in inputs.links:
                depth = max(depth, link.from_node.depth + 1)
        self.update_depth(depth) # not good...

#    def copy(self, node):

    def update_depth(self, depth):
            if self.depth == depth:
                return
            self.depth = depth
            for output in self.outputs:
                for link in output.links:
                    link.to_node.update_depth(self.depth + 1)

def input_ast(self: bpy.types.Node, socket: bpy.types.NodeSocket):
    links = socket.links
    if len(links) == 0:
        return None
    if not hasattr(links[0].from_node, "ast"):
        return None
    return links[0].from_node.ast()

def update_literal_value(self, context):
    # 無限ループ防止のため、値が変化している場合のみ代入する
    try:
        v_int = int(float(self.value)) # float経由で "1.0" などの文字列にも対応
        if self.value_int != v_int:
            self.value_int = v_int
    except: pass
    v_float = None
    try:
        v_float = float(self.value)
        if self.value_float != v_float:
            self.value_float = v_float
    except: pass
    # 文字列からのブール値変換
    v_bool = bool(v_float) if v_float is not None else \
            self.value.lower() not in ("false", "none", "[]", "{}", "set()", "dict()", "0j", "0+0j", "") # より良い方法を探す
    if self.value_bool != v_bool:
        self.value_bool = v_bool

def update_literal_int(self, context):
    v_float = float(self.value_int)
    if self.value_float != v_float:
        self.value_float = v_float
    v_bool = bool(self.value_int)
    if self.value_bool != v_bool:
        self.value_bool = v_bool
    v_str = str(self.value_int)
    if self.value != v_str:
        self.value = v_str

def update_literal_float(self, context):
    v_str = str(self.value_float)
    if self.value != v_str:
        self.value = v_str
    v_int = int(self.value_float)
    if self.value_int != v_int:
        self.value_int = v_int
    v_bool = bool(self.value_float)
    if self.value_bool != v_bool:
        self.value_bool = v_bool

def update_literal_bool(self, context):
    v_str = str(self.value_bool)
    if self.value != v_str:
        self.value = v_str
    v_int = int(self.value_bool)
    if self.value_int != v_int:
        self.value_int = v_int
    v_float = float(self.value_bool)
    if self.value_float != v_float:
        self.value_float = v_float

class LiteralNode(PythonBaseNode):
    bl_idname = "LiteralNode"
    bl_label = "Literal"

    op_type: bpy.props.EnumProperty( # type: ignore
        name="Operation",
        items=[
            ("variable", "Variable", "Variable"),
            ("None", "None", "None"),
            ("int", "Integer (int)", "Integer"),
            ("float", "Float (float)", "Float"),
            ("bool", "Boolean (bool)", "Boolean"),
            ("str", "String (str)", "String"),
            ("list", "List ([...])", "List"),
            ("array", "Array (np.array(...))", "Array"),
            ("tensor", "Tensor (torch.tensor(...))", "Tensor"),
            #("dict", "Dictionary ({})", "Dictionary"),
            #("tuple", "Tuple (())", "Tuple"),
            #("set", "Set ({})", "Set"),
            #("ellipsis", "Ellipsis (...)", "Ellipsis"),
            #("bytes", "Bytes (b'')", "Bytes"),
            #("complex", "Complex (j)", "Complex"),
            #("slice", "Slice ([:])", "Slice"),
            #("joined_str", "Joined String (f-string)", "Joined String"),
            #("constant", "Constant", "Constant"),
            #("attribute", "Attribute (obj.attr)", "Attribute"),
            #("subscript", "Subscript (obj[key])", "Subscript"),
            #("call", "Call (func())", "Call"),
            #("name", "Name (variable)", "Name"),
        ],
        default="variable",
    )
    value: bpy.props.StringProperty(name="Value", default="", update=update_literal_value)  # type: ignore
    value_int: bpy.props.IntProperty(name="Integer Value", default=0, update=update_literal_int)  # type: ignore
    value_float: bpy.props.FloatProperty(name="Float Value", default=0.0, update=update_literal_float)  # type: ignore
    value_bool: bpy.props.BoolProperty(name="Boolean Value", default=False, update=update_literal_bool)  # type: ignore

    def init(self, context):
        self.outputs.new("PythonValueSocket", "Value")

    def draw_buttons(self, context, layout):
        layout.prop(self, "op_type", text="")
        if self.op_type == "None":
            pass
        elif self.op_type == "int":
            layout.prop(self, "value_int", text="")
        elif self.op_type == "float":
            layout.prop(self, "value_float", text="")
        elif self.op_type == "bool":
            layout.prop(self, "value_bool", text="")
        else:
            layout.prop(self, "value", text="")

    def ast(self):
        if self.op_type == "variable":
            return ast.Name(id=self.value, ctx=ast.Load())
        elif self.op_type == "None":
            return ast.Constant(value=None)
        elif self.op_type == "int":
            return ast.Constant(value=self.value_int)
        elif self.op_type == "float":
            return ast.Constant(value=self.value_float)
        elif self.op_type == "bool":
            return ast.Constant(value=self.value_bool)
        elif self.op_type == "str":
            return ast.Constant(value=self.value)
        elif self.op_type == "list":
            # Simple parsing for list literals or empty list
            try:
                return ast.parse(self.value if self.value.strip() else "[]", mode='eval').body # TODO: security fix
            except:
                return ast.List(elts=[], ctx=ast.Load())
        elif self.op_type in {"array", "tensor"}:
            func_name = "np.array" if self.op_type == "array" else "torch.tensor"
            try:
                args_ast = ast.parse(self.value, mode='eval').body # TODO: security fix
                return ast.Call(
                    func=ast.Attribute(value=ast.Name(id=func_name.split('.')[0], ctx=ast.Load()), 
                                     attr=func_name.split('.')[1], ctx=ast.Load()) if '.' in func_name else ast.Name(id=func_name, ctx=ast.Load()),
                    args=[args_ast],
                    keywords=[]
                )
            except:
                return ast.Name(id=self.value, ctx=ast.Load())
        return None
        

# tree = ast.parse("_1+_2")
# print(ast.dump(tree, indent=2))

# それぞれのASTを一意な変数に入れる

# >>> a = ast.parse("f = lambda: 12+12")
# >>> compiled = compile(a, filename="<string>", mode="exec")
# >>> exec(compiled, ns)
# >>> ns["f"]
# <function <lambda> at 0x7a14d1ced4e0>
# >>> ns["f"]()
# 24
# >>> torch.compile(ns["f"])()
# 24

# >>> import torch.fx
# >>> gm = torch.fx.symbolic_trace(ns["f"])
# >>> gm.graph.print_tabular()
# opcode    name    target    args    kwargs
# --------  ------  --------  ------  --------
# output    output  output    (24,)   {}


# 別プロセスのsandboxで実行してキューに入れてper-frameでUI更新？
# 途中の計算結果を表示するか否か→表示できると何かと便利だけど最適化とのトレードオフ


import sys
# import os
import subprocess
import importlib

# TODO: 非同期実行、ユーザーへの確認

def get_modules_path():
    """Blenderのユーザー用 scripts/modules ディレクトリのパスを取得する。"""
    # 例: /home/nazo/.config/blender/5.1/scripts/modules
    return bpy.utils.user_resource('SCRIPTS', path="modules", create=True)

def import_pytorch():
    # インストール先を検索パスに追加
    modules_path = get_modules_path()
    if modules_path not in sys.path:
        sys.path.append(modules_path)

    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
        return torch
    except (ImportError, ModuleNotFoundError):
        print("PyTorch is not installed. Attempting to install...")
        if install_pytorch():
            # インポートキャッシュをクリアして再試行
            importlib.invalidate_caches()
            try:
                import torch
                return torch
            except ImportError:
                print("PyTorch installed but could not be imported. A restart might be required.")
        return None
    except Exception as e:
        print(f"Error checking PyTorch: {e}")
        return None
import re

def get_system_cuda_version():
    """Determines the CUDA version supported by the driver or toolkit."""
    try:
        output = subprocess.check_output(["nvidia-smi"], stderr=subprocess.DEVNULL).decode()
        match = re.search(r"CUDA Version:\s+(\d+\.\d+)", output)
        if match: return match.group(1)
    except: pass
#    try: # unchecked yet
#        output = subprocess.check_output(["nvcc", "--version"], stderr=subprocess.DEVNULL).decode()
#        match = re.search(r"release\s+(\d+\.\d+)", output)
#        if match: return match.group(1)
#    except: pass
    return None

# XXX: untested
def install_pytorch():
    """PyTorchのインストールを試行。成功ならTrueを返す。"""
#    try:
#        result = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
#            capture_output=True,
#            text=True,
#            check=True)
#        print(result.stdout)
#    except subprocess.CalledProcessError as e:
#        print(f"Error updating pip: {e.stderr}")

    # install pytorch
    target_dir = get_modules_path()
    cuda_version = get_system_cuda_version()
    
    if cuda_version:
        print(f"Found CUDA {cuda_version}. Installing compatible PyTorch...")
    else:
        print("CUDA not detected. Installing standard PyTorch (CPU or bundled CUDA)...")

    try:
        # --target allows installing into Blender's user modules directory
        cmd = [sys.executable, "-m", "pip", "install", "--target", target_dir, "torch"]

        if cuda_version: # not checked yet
            # Install with specific CUDA index if version is detected
            major_minor = cuda_version.split('.')
            cu_tag = f"cu{major_minor[0]}{major_minor[1]}"
            # Check https://download.pytorch.org/whl/{cu_tag} is available
            import urllib.request
            try:
                with urllib.request.urlopen(f"https://download.pytorch.org/whl/{cu_tag}", timeout=2) as response:
                    if response.status == 200:
                        cmd.extend(["--extra-index-url", f"https://download.pytorch.org/whl/{cu_tag}"])
            except:
                # TODO: Fallback to older CUDA version?
                pass

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing PyTorch: {e.stderr}")
        return False

# XXX: untested
def uninstall_pytorch():
    """PyTorchのアンインストールを試行。"""
    target_dir = get_modules_path()
    try:
        # -y to bypass confirmation
        cmd = [sys.executable, "-m", "pip", "uninstall", "--target", target_dir, "-y", "torch"]
        # Note: pip uninstall doesn't usually support --target,
        # but it will find it if it's in the path or we can manually remove the directory.
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)

        # Manually cleanup the directory if pip didn't catch it in the target_dir
#        torch_dir = Path(target_dir) / "torch"
#        if torch_dir.exists():
#            shutil.rmtree(torch_dir)
#            print(f"Manually removed {torch_dir}")
            
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error uninstalling PyTorch: {e.stderr}")
        return False


from pathlib import Path
import os
import shutil

app_template_init_file = """import addon_utils

def register():
    addon_utils.enable("%s", default_set=True)

def unregister():
    pass
""" % __package__

def install_app_template():
    # https://docs.blender.org/manual/en/latest/advanced/app_templates.html
    # 標準では存在しないものの、作れば即時認識される模様
    tp = Path(bpy.utils.script_path_user()) / "startup" / "bl_app_templates_user"
    p = tp / "Python_Nodes"
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)
        print("created: %s" % p)

    if str(tp) not in bpy.utils.app_template_paths(): # テンプレートパスとして認識されてるか確認
        print("App template path not found: %s" % p)
        return

    to_p = p / "startup.blend"
    from_p = Path(__file__).parent / "startup.blend"
    if not p.exists():
        try:
            os.symlink(from_p, to_p, target_is_directory=False)
        except:
            try:
                # Windows requires admin or specific privileges for symlinks, 
                # but we can try to create a hard link or just copy if it fails.
                shutil.copy(from_p, to_p)
            except Exception as e:
                print(f"Failed to copy startup.blend: {e}")
                return

        print("created: %s" % to_p)

    ip = p / "__init__.py"
    if not ip.exists():
        try:
            with open(ip, "w", encoding="utf-8") as f_out:
                f_out.write(app_template_init_file)
        except Exception as e:
            print(f"Failed to create app template init: {e}")
            return

        print("created: %s" % (p / "__init__.py"))

class PythonNodesPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    bl_label = "Add-on Preferences"

    def draw(self, context):
        layout = self.layout
        layout.operator("node.uninstall_python_node", icon='TRASH')

def uninstall_app_template():
    p = Path(bpy.utils.script_path_user()) / "startup" / "bl_app_templates_user" / "Python_Nodes"
    if p.exists():
        try:
            shutil.rmtree(p)
            print("uninstalled: %s" % p)
        except Exception as e:
            print(f"Failed to uninstall app template: {e}")

# TODO: アンインストールを実装する
class MY_OT_UninstallPythonNode(bpy.types.Operator):
    bl_idname = "node.uninstall_python_node"
    bl_label = "Uninstall Python Nodes extension (WIP)"
    bl_description = "Remove the Python Nodes extension"

    def execute(self, context):
        uninstall_app_template()
        self.report({'INFO'}, "App Template Uninstalled")
#        uninstall_pytorch()
#        self.report({'INFO'}, "PyTorch Uninstalled")

#        bpy.ops.extensions.package_uninstall(pkg_id=__package__) # repo_directory="..." ?
#        self.report({'INFO'}, "Python Nodes Uninstalled")

        return {'FINISHED'}

# Python Operators
# https://docs.python.org/ja/3/library/operator.html
# https://docs.python.org/3/library/ast.html
# https://docs.python.org/3/genindex-_.html
# https://docs.python.org/3/library/functions.html
# https://docs.pytorch.org/docs/2.12/fx.html

# TODO: Inplace演算問題（配列操作含む） -> geometry nodesはどうしてる？
# 配列参照と配列スライスは直ぐに実装できるはず
# length_hint
# call -> 副作用問題、セキュリティ問題
# 組み込み関数、mathの二項演算子、三項演算子
# argmax -> 通常の配列に使えない問題

class UnaryOpNode(PythonBaseNode):
    bl_idname = "UnaryOpNode"
    bl_label = "Unary Op"

    op_type: bpy.props.EnumProperty( # type: ignore
        name="Operation",
        items=[
            ("Pos", "Pos (+)", "Positive"),
            ("Neg", "Neg (-)", "Negative"),
            ("Not", "Not (!)", "Logical Not"),
            ("Invert", "Invert (~)", "Bitwise Invert"),
            ("IsNone", "Is None (is None)", "Check if None"),
            ("IsNotNone","Is Not None (is not None)", "Check if not None"),
            ("Int","To Int (int(a))", "Convert to integer"),
            ("Float","To Float (float(a))", "Convert to float"),
            ("Bool","To Bool (bool(a))", "Convert to boolean"), # operatorだとtruth
            ("Str","To Str (str(a))", "Convert to string"),
            ("Len", "Length (len(a))", "Get length of sequence"),
            ("Abs", "Absolute (abs(a))", "Get absolute value"),
            ("Round", "Round (round(a))", "Round to nearest integer"),
            ("Ceil", "Ceil (math.ceil(a))", "Round up to nearest integer"),
            ("Floor", "Floor (math.floor(a))", "Round down to nearest integer"),
            ("Trunc", "Trunc (math.trunc(a))", "Truncate to integer"),

#            ("Sum", "Sum (sum(a))", "Sum of elements"),
#            ("Min", "Min (min(a))", "Minimum value"),
#            ("Max", "Max (max(a))", "Maximum value"),
#            ("Sorted", "Sorted (sorted(a))", "Return a new sorted list"),
#            ("Reversed", "Reversed (reversed(a))", "Return a reverse iterator"),
#            ("Set", "To Set (set(a))", "Convert to set"),
#            ("List", "To List (list(a))", "Convert to list"),
#            ("Tuple", "To Tuple (tuple(a))", "Convert to tuple"),

            ("Index", "To Index (a.__index__())", "Convert to a exact integer"),
        ],
        default="Neg",
    )

    def init(self, context):
        self.inputs.new("PythonValueSocket", "Value")
        self.outputs.new("PythonValueSocket", "Result")

    def draw_label(self):
        return self.op_type

    def draw_buttons(self, context, layout):
        layout.prop(self, "op_type", text="")

    def ast(self):
        operand = input_ast(self, self.inputs["Value"])
        if not operand:
            return None

        if self.op_type == "Index":
            # a.__index__()
            return ast.Call(
                func=ast.Attribute(
                    value=operand,
                    attr='__index__',
                    ctx=ast.Load()
                ),
                args=[],
                keywords=[]
            )

        # Type conversion and math functions
        if self.op_type in {"Int", "Float", "Bool", "Str", "Len", "Abs", "Round"}:
            func_map = {
                "Int": "int", "Float": "float", "Bool": "bool", 
                "Str": "str", "Len": "len", "Abs": "abs", "Round": "round"
            }
            return ast.Call(
                func=ast.Name(id=func_map[self.op_type], ctx=ast.Load()),
                args=[operand],
                keywords=[]
            )
        
        if self.op_type in {"Ceil", "Floor", "Trunc"}:
            func_map = {"Ceil": "ceil", "Floor": "floor", "Trunc": "trunc"}
            return ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='math', ctx=ast.Load()),
                    attr=func_map[self.op_type],
                    ctx=ast.Load()
                ),
                args=[operand],
                keywords=[]
            )

        compare_ops = {
            "IsNone": ast.Is,
            "IsNotNone": ast.IsNot,
        }
        if self.op_type in compare_ops:
            return ast.Compare(left=operand, ops=[compare_ops[self.op_type]()], comparators=[ast.Constant(value=None)])

        unary_ops = {
            "Pos": ast.UAdd,
            "Neg": ast.USub,
            "Not": ast.Not,
            "Invert": ast.Invert,
        }
        return ast.UnaryOp(op=unary_ops[self.op_type](), operand=operand)

class BinOpNode(PythonBaseNode):
    bl_idname = "BinOpNode"
    bl_label = "Binary Op"

    op_type: bpy.props.EnumProperty( # type: ignore
        name="Operation",
        items=[
            ("Add", "Add (+)", "Addition"),
#            ("Concat", "Concat (seq + seq)", "Concatenation"),
            ("Sub", "Sub (-)", "Subtraction"),
            ("Mul", "Mul (*)", "Multiplication"),
            ("TrueDiv", "TrueDiv (/)", "True Division"),
            ("FloorDiv", "FloorDiv (//)", "Floor Division"),
            ("Mod", "Mod (%)", "Modulo"),
            ("Pow", "Pow (**)", "Power"),
            ("LShift", "LShift (<<)", "Left Shift"),
            ("RShift", "RShift (>>)", "Right Shift"),
            ("BitOr", "BitOr (|)", "Bitwise OR"),
            ("BitXor", "BitXor (^)", "Bitwise XOR"),
            ("BitAnd", "BitAnd (&)", "Bitwise AND"),
            ("MatMul", "MatMul (@)", "Matrix Multiplication"),
            ("And", "And (and)", "Logical And"),
            ("Or", "Or (or)", "Logical Or"),
            ("Eq", "Eq (==)", "Equal"),
            ("Ne", "Ne (!=)", "Not Equal"),
            ("Lt", "Lt (<)", "Less Than"),
            ("Le", "Le (<=)", "Less Than or Equal"),
            ("Gt", "Gt (>)", "Greater Than"),
            ("Ge", "Ge (>=)", "Greater Than or Equal"),
            ("Is", "Is (is)", "Identity Is"),
            ("IsNot", "IsNot (is not)", "Identity Is Not"),
            ("In", "In (in)", "Membership In"),
            ("NotIn", "NotIn (not in)", "Membership Not In"),
        ],
        default="Add",
    )

    def init(self, context):
        self.inputs.new("PythonValueSocket", "Left")
        self.inputs.new("PythonValueSocket", "Right")
        self.outputs.new("PythonValueSocket", "Result")

    def draw_label(self):
        return self.op_type

    def draw_buttons(self, context, layout):
        layout.prop(self, "op_type", text="")

    def ast(self):
        left = input_ast(self, self.inputs["Left"])
        right = input_ast(self, self.inputs["Right"])
        if not left or not right:
            return None

        # Logical operations (and, or)
        if self.op_type in {"And", "Or"}:
            op = ast.And if self.op_type == "And" else ast.Or
            return ast.BoolOp(op=op(), values=[left, right])

        # Comparison operations (==, !=, <, <=, >, >=, is, is not, in, not in)
        compare_ops = {
            "Eq": ast.Eq, "Ne": ast.NotEq,
            "Lt": ast.Lt, "Le": ast.LtE,
            "Gt": ast.Gt, "Ge": ast.GtE,
            "Is": ast.Is, "IsNot": ast.IsNot,
            "In": ast.In, "NotIn": ast.NotIn,
        }
        if self.op_type in compare_ops:
            return ast.Compare(left=left, ops=[compare_ops[self.op_type]()], comparators=[right])

        if self.op_type in {"Concat"}:
            # return ast.BinOp(left=left, op=ast.Add(), right=right) # not good
            return ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='operator', ctx=ast.Load()),
                    attr='concat',
                    ctx=ast.Load()
                ),
                args=[left, right],
                keywords=[]
            )

        # Arithmetic and bitwise operations
        bin_ops = {
            "Add": ast.Add, "Sub": ast.Sub, "Mul": ast.Mult,
            "TrueDiv": ast.Div, "FloorDiv": ast.FloorDiv, "Mod": ast.Mod,
            "Pow": ast.Pow, "LShift": ast.LShift, "RShift": ast.RShift,
            "BitOr": ast.BitOr, "BitXor": ast.BitXor, "BitAnd": ast.BitAnd,
            "MatMul": ast.MatMult,
        }
        return ast.BinOp(left=left, op=bin_ops[self.op_type](), right=right)

class PrintNode(PythonBaseNode):
    bl_idname = "PrintNode"
    bl_label = "Print"

    def init(self, context):
        self.inputs.new("PythonValueSocket", "Value")

    def ast(self):
        val_ast = input_ast(self, self.inputs["Value"])
        if not val_ast: # not needed
            val_ast = ast.Constant(value=None)
        return ast.Expr(value=ast.Call(
            func=ast.Name(id='print', ctx=ast.Load()),
            args=[val_ast],
            keywords=[]
        ))

# =====================================================
# Node UI Category
# =====================================================
class MyCategory(NodeCategory):
    if TYPE_CHECKING: # XXX: workaround the bug in fake-bpy-module
        def __init__(self, identifier, name, *, description="", items=None) -> None:
            ...

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return (
            space
            and hasattr(space, "tree_type")
            and space.tree_type == "PythonNodeTree"
        )


node_categories = [
    MyCategory(
        "BASIC_PYTHON_NODES",
        "Basic Python Nodes",
        items=[NodeItem("LiteralNode"),
               NodeItem("BinOpNode"),
               NodeItem("UnaryOpNode", label="Pos", settings={"op_type": "'Pos'"}),
               NodeItem("UnaryOpNode", label="Neg", settings={"op_type": "'Neg'"}),
               NodeItem("UnaryOpNode", label="Not", settings={"op_type": "'Not'"}),
               NodeItem("UnaryOpNode", label="Invert", settings={"op_type": "'Invert'"}),
               NodeItem("UnaryOpNode", label="IsNone", settings={"op_type": "'IsNone'"}),
               NodeItem("UnaryOpNode", label="IsNotNone", settings={"op_type": "'IsNotNone'"}),
               NodeItem("UnaryOpNode", label="Index", settings={"op_type": "'Index'"}),
               NodeItem("UnaryOpNode", label="Int", settings={"op_type": "'Int'"}),
               NodeItem("UnaryOpNode", label="Float", settings={"op_type": "'Float'"}),
               NodeItem("UnaryOpNode", label="Bool", settings={"op_type": "'Bool'"}),
               NodeItem("UnaryOpNode", label="Str", settings={"op_type": "'Str'"}),
               NodeItem("UnaryOpNode", label="Len", settings={"op_type": "'Len'"}),
               NodeItem("UnaryOpNode", label="Abs", settings={"op_type": "'Abs'"}),
               NodeItem("UnaryOpNode", label="Round", settings={"op_type": "'Round'"}),
               NodeItem("UnaryOpNode", label="Ceil", settings={"op_type": "'Ceil'"}),
               NodeItem("UnaryOpNode", label="Floor", settings={"op_type": "'Floor'"}),
               NodeItem("UnaryOpNode", label="Trunc", settings={"op_type": "'Trunc'"}),

               NodeItem("BinOpNode", label="Add", settings={"op_type": "'Add'"}),
#               NodeItem("BinOpNode", label="Concat", settings={"op_type": "'Concat'"}),
               NodeItem("BinOpNode", label="Sub", settings={"op_type": "'Sub'"}),
               NodeItem("BinOpNode", label="Mul", settings={"op_type": "'Mul'"}),
               NodeItem("BinOpNode", label="TrueDiv", settings={"op_type": "'Div'"}),
               NodeItem("BinOpNode", label="FloorDiv", settings={"op_type": "'FloorDiv'"}),
               NodeItem("BinOpNode", label="Mod", settings={"op_type": "'Mod'"}),
               NodeItem("BinOpNode", label="Pow", settings={"op_type": "'Pow'"}),
               NodeItem("BinOpNode", label="LShift", settings={"op_type": "'LShift'"}),
               NodeItem("BinOpNode", label="RShift", settings={"op_type": "'RShift'"}),
               NodeItem("BinOpNode", label="BitOr", settings={"op_type": "'BitOr'"}),
               NodeItem("BinOpNode", label="BitXor", settings={"op_type": "'BitXor'"}),
               NodeItem("BinOpNode", label="BitAnd", settings={"op_type": "'BitAnd'"}),
               NodeItem("BinOpNode", label="MatMul", settings={"op_type": "'MatMul'"}),
               NodeItem("BinOpNode", label="And", settings={"op_type": "'And'"}),
               NodeItem("BinOpNode", label="Or", settings={"op_type": "'Or'"}),
               NodeItem("BinOpNode", label="Eq", settings={"op_type": "'Eq'"}),
               NodeItem("BinOpNode", label="Ne", settings={"op_type": "'NotEq'"}),
               NodeItem("BinOpNode", label="Lt", settings={"op_type": "'Lt'"}),
               NodeItem("BinOpNode", label="Le", settings={"op_type": "'Le'"}),
               NodeItem("BinOpNode", label="Gt", settings={"op_type": "'Gt'"}),
               NodeItem("BinOpNode", label="Ge", settings={"op_type": "'Ge'"}),
               NodeItem("BinOpNode", label="Is", settings={"op_type": "'Is'"}),
               NodeItem("BinOpNode", label="IsNot", settings={"op_type": "'IsNot'"}),
               NodeItem("BinOpNode", label="In", settings={"op_type": "'In'"}),
               NodeItem("BinOpNode", label="NotIn", settings={"op_type": "'NotIn'"}),
               NodeItem("PrintNode"),
               ],
    )
]

import numpy as np
def nodetree_to_ast(self: bpy.types.Operator, context: bpy.types.Context):
    tree = context.space_data.edit_tree
    if not tree:
        return ast.Module(body=[], type_ignores=[])

    # 有効なPythonノードのみ抽出
    nodes = [n for n in tree.nodes if hasattr(n, "depth") and hasattr(n, "ast")]
    if not nodes:
        return ast.Module(body=[], type_ignores=[])

    prios = np.array([n.depth for n in nodes], dtype=int)
    sorted_indices = np.argsort(prios)

    body = []
    for idx in sorted_indices:
        node = nodes[idx]
        
        # そのノードの出力がどこにも接続されていない場合、
        # それをトップレベルの実行文（Statement/Expression）として扱う
        is_statement = True
        for output in node.outputs:
            if output.links:
                is_statement = False
                break
        
        if is_statement:
            node_ast = node.ast()
            if node_ast:
                self.report({'INFO'}, "Generated AST Body: %s" % ast.dump(node_ast))
                # 式ノードの場合は ast.Expr でラップする
                if not isinstance(node_ast, (ast.stmt, ast.Module)):
                    node_ast = ast.Expr(value=node_ast)
                body.append(node_ast)
    
    return ast.Module(body=body, type_ignores=[])
    
# 実行ボタンを作る
class MY_OT_ExecutePythonNodeTree(bpy.types.Operator):
    bl_idname = "node.execute_python_node_tree"
    bl_label = "Execute Python Node Tree"
    bl_description = "Execute the logic of the current Python node tree"

    def execute(self, context):
        self.report({'INFO'}, "Python Node Tree Execution Started")
        self.report({'INFO'}, ast.unparse(nodetree_to_ast(self, context)))
        # 実行前にPyTorchの存在を確認し、必要ならインストールを促す
        #tree = context.space_data.edit_tree
        #needs_torch = any(getattr(n, "op_type", None) == 'tensor' for n in tree.nodes)
        
        #if needs_torch:
        #    self.report({'INFO'}, "Checking PyTorch...")
        #    if not import_pytorch():
        #        self.report({'ERROR'}, "PyTorch is required for Tensor nodes but could not be loaded.")
        #        return {'CANCELLED'}

        # ASTの生成
        #ast_module = nodetree_to_ast(self, context)
        
        #self.report({'INFO'}, "Python Node Tree: AST Generated")
        #self.report({'INFO'}, ast.unparse(ast_module))
        return {'FINISHED'}

def draw_node_header(self, context):
    if context.space_data.tree_type == "PythonNodeTree":
        layout = self.layout
        layout.operator("node.execute_python_node_tree", icon='PLAY')


# =====================================================
# Register
# =====================================================
classes = [
    PythonNodesPreferences,
    PythonNodeTree,
    PythonValueSocket,
    LiteralNode,
    BinOpNode,
    UnaryOpNode,
    PrintNode,
    MY_OT_ExecutePythonNodeTree,
    MY_OT_UninstallPythonNode,
]

def register():
    unregister()
    install_app_template()
    for c in classes:
        bpy.utils.register_class(c)

    register_node_categories("MY_NODES_CAT", node_categories)
    bpy.types.NODE_HT_header.append(draw_node_header)


def unregister():
    try:
        bpy.types.NODE_HT_header.remove(draw_node_header)
    except Exception:
        pass

    try:
        unregister_node_categories("MY_NODES_CAT")
    except Exception:
        pass

    for c in reversed(classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass

if __name__ == "__main__":
    register()