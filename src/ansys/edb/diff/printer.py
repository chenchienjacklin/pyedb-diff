from __future__ import annotations
from enum import Enum
from abc import ABC, abstractmethod
import os
import sys



class DiffTreeBuilderBase(ABC):
    @abstractmethod
    def build(self, diff_json: dict) -> DiffTreeNode:
        pass


class PrinterBase(ABC):
    @abstractmethod
    def print(self, node: DiffTreeNode, prefix: str = "", is_last: bool = True):
        pass


class DiffTreeNodeType(Enum):
    INTERNAL = "internal"
    LEAF = "leaf"
    OBJECT = "object"
 
 
class DiffTreeNode:
    def __init__(self, name: str, node_type: DiffTreeNodeType = DiffTreeNodeType.INTERNAL, diff_value: tuple = None):
        self.name = name
        self.node_type = node_type
        self.diff_value = diff_value  # (val1, val2, is_equal) for leaves
        self.children: list[DiffTreeNode] = []
        self.parent: DiffTreeNode = None
 
    def add_child(self, child: DiffTreeNode):
        child.parent = self
        self.children.append(child)
 
    def is_leaf(self):
        return self.node_type == DiffTreeNodeType.LEAF
 
    def has_diff(self):
        if self.is_leaf() and self.diff_value:
            return not self.diff_value[2]  # is_equal is False
        return any(child.has_diff() for child in self.children)
   
 
class DiffTreeBuilderV1(DiffTreeBuilderBase):
    def __init__(self):
        self.root = None
 
    def build(self, diff_json: dict) -> DiffTreeNode:
        """Build tree from diff JSON."""
        self.root = DiffTreeNode("database", DiffTreeNodeType.INTERNAL)
        self._build_recursive(diff_json.get("database", {}), self.root)
        return self.root
 
    def _build_recursive(self, data, parent_node: DiffTreeNode):
        if isinstance(data, dict):
            for key, value in data.items():
                child = self._process_value(key, value)
                parent_node.add_child(child)
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    # Object in list - use id if available
                    obj_id = self._extract_id(item)
                    diff_status = self._extract_diff_status(item)
                    child = DiffTreeNode(f"[{idx}] id={obj_id} ({diff_status})", DiffTreeNodeType.OBJECT)
                    self._build_recursive(item, child)
                    parent_node.add_child(child)
 
    def _process_value(self, key: str, value):
        if self._is_diff_tuple(value):
            # Leaf node with diff value
            node = DiffTreeNode(key, DiffTreeNodeType.LEAF, diff_value=tuple(value))
            return node
        elif isinstance(value, dict):
            node = DiffTreeNode(key, DiffTreeNodeType.INTERNAL)
            self._build_recursive(value, node)
            return node
        elif isinstance(value, list):
            node = DiffTreeNode(key, DiffTreeNodeType.INTERNAL)
            self._build_recursive(value, node)
            return node
        else:
            return DiffTreeNode(key, DiffTreeNodeType.LEAF, diff_value=(str(value), None, True))
 
    def _is_diff_tuple(self, value):
        """Check if value is a diff tuple [val1, val2, is_equal]."""
        return (
            (isinstance(value, tuple) or isinstance(value, list))
            and len(value) == 3
            and isinstance(value[2], bool)
        )
 
    def _extract_id(self, item: dict) -> str:
        if "id" in item and self._is_diff_tuple(item["id"]):
            return item["id"][1]
        if "name" in item and self._is_diff_tuple(item["name"]):
            return item["name"][1]
        return "?"
    
    def _extract_diff_status(self, item: dict) -> str:
        id1 = id2 = None
        if "id" in item and self._is_diff_tuple(item["id"]):
            id1, id2, _ = item["id"]
        elif "name" in item and self._is_diff_tuple(item["name"]):
            id1, id2, _ = item["name"]
        
        if id1 is None or id1 == "None":
            return "added"
        elif id2 is None or id2 == "None":
            return "removed"
        else:
            return "modified"
        return "?"


class DiffTreePrinterV1(PrinterBase):
    """Print tree in ASCII format."""
   
    # ANSI colors
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    _encoding_configured = False


    def __init__(self, show_equal=False):
        self.show_equal = show_equal
        self._ensure_utf8_output()

    def print(self, node: DiffTreeNode, prefix="", is_last=True):
        connector = "└── " if is_last else "├── "
       
        if node.is_leaf() and node.diff_value:
            val1, val2, is_equal = node.diff_value
            if is_equal and not self.show_equal:
                return
            print(f"{prefix}{connector}{node.name}: {self.GREEN}{val1}{self.RESET} → {self.RED}{val2}{self.RESET}")
        else:
            print(f"{prefix}{connector}{node.name}")
 
        child_prefix = prefix + ("    " if is_last else "│   ")
        children = node.children
        if not self.show_equal:
            children = [c for c in children if c.has_diff()]
       
        for i, child in enumerate(children):
            self.print(child, child_prefix, i == len(children) - 1)
    
    @classmethod
    def _ensure_utf8_output(cls):
        if cls._encoding_configured:
            return
        if os.name == "nt":  # Windows console
            for stream in (sys.stdout, sys.stderr):
                if hasattr(stream, "reconfigure"):
                    try:
                        stream.reconfigure(encoding="utf-8", errors="replace")
                    except Exception:
                        pass
        cls._encoding_configured = True
