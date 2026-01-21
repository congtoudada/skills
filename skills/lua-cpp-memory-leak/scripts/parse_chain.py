#!/usr/bin/env python3
"""
Reference Chain Parser for Lua-C++ Memory Leak Analysis

Parses reference chain strings into structured data for easier analysis.

Usage:
    python parse_chain.py <reference_chain>

Example:
    python parse_chain.py "IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[false]._crossoverLabel.IVComponentBase:000000029EAF72C0[false]"

Output:
    JSON structure with parsed nodes and leak analysis
"""

import sys
import re
import json
from typing import List, Dict, Optional


class ReferenceNode:
    """Represents a single node in the reference chain."""
    
    def __init__(self, class_name: str, address: str, released: bool, field: Optional[str] = None):
        self.class_name = class_name
        self.address = address
        self.released = released
        self.field = field  # Field name from parent to this node
        
    def to_dict(self) -> Dict:
        return {
            "class_name": self.class_name,
            "address": self.address,
            "released": self.released,
            "field": self.field,
            "is_leak": not self.released
        }
    
    def __repr__(self):
        released_str = "Released" if self.released else "NOT RELEASED"
        field_str = f" (via {self.field})" if self.field else ""
        return f"{self.class_name}:{self.address} [{released_str}]{field_str}"


class ReferenceChain:
    """Represents a complete reference chain."""
    
    def __init__(self, chain_str: str):
        self.raw_chain = chain_str
        self.nodes: List[ReferenceNode] = []
        self.parse()
        
    def parse(self):
        """Parse the reference chain string into nodes."""
        # Pattern: ClassName:Address[true/false]
        # Connected by .fieldName.
        
        parts = self.raw_chain.split('.')
        
        current_field = None
        for i, part in enumerate(parts):
            # Extract class name, address, and release status
            # Pattern: ClassName:HexAddress[bool] or just fieldName
            
            # Check if this part contains a class definition
            class_match = re.match(r'^([A-Za-z0-9_]+):([0-9A-Fa-f]+)\[(true|false)\]$', part)
            
            if class_match:
                class_name = class_match.group(1)
                address = class_match.group(2)
                released = class_match.group(3) == 'true'
                
                node = ReferenceNode(class_name, address, released, current_field)
                self.nodes.append(node)
                current_field = None
            else:
                # This is a field name
                current_field = part
                
    def get_leak_nodes(self) -> List[ReferenceNode]:
        """Return all nodes that have not called Release."""
        return [node for node in self.nodes if not node.released]
    
    def get_first_leak(self) -> Optional[ReferenceNode]:
        """Return the first node in chain that hasn't called Release."""
        leak_nodes = self.get_leak_nodes()
        return leak_nodes[0] if leak_nodes else None
    
    def get_parent(self, node: ReferenceNode) -> Optional[ReferenceNode]:
        """Get the parent node of a given node."""
        try:
            idx = self.nodes.index(node)
            return self.nodes[idx - 1] if idx > 0 else None
        except ValueError:
            return None
    
    def get_children(self, node: ReferenceNode) -> List[ReferenceNode]:
        """Get all child nodes of a given node."""
        try:
            idx = self.nodes.index(node)
            return self.nodes[idx + 1:]
        except ValueError:
            return []
    
    def visualize(self) -> str:
        """Create a visual tree representation of the chain."""
        lines = []
        for i, node in enumerate(self.nodes):
            indent = "  " * i
            if i > 0:
                indent += "└─ "
                if node.field:
                    indent += f"{node.field} → "
            
            status = "Released ✓" if node.released else "NOT RELEASED ⚠️"
            lines.append(f"{indent}{node.class_name} [{status}]")
        
        return "\n".join(lines)
    
    def analyze(self) -> Dict:
        """Perform analysis and return structured results."""
        leak_nodes = self.get_leak_nodes()
        first_leak = self.get_first_leak()
        
        analysis = {
            "raw_chain": self.raw_chain,
            "total_nodes": len(self.nodes),
            "leaked_nodes": len(leak_nodes),
            "nodes": [node.to_dict() for node in self.nodes],
            "visualization": self.visualize(),
            "leaks": []
        }
        
        # Analyze each leak
        for leak_node in leak_nodes:
            parent = self.get_parent(leak_node)
            children = self.get_children(leak_node)
            
            leak_info = {
                "node": leak_node.to_dict(),
                "parent": parent.to_dict() if parent else None,
                "parent_released": parent.released if parent else None,
                "has_children": len(children) > 0,
                "children_count": len(children),
                "priority": "high" if parent and parent.released else "medium"
            }
            
            analysis["leaks"].append(leak_info)
        
        return analysis
    
    def to_dict(self) -> Dict:
        """Convert entire chain to dictionary."""
        return self.analyze()


def parse_multiple_chains(chain_strings: List[str]) -> Dict:
    """Parse multiple reference chains and provide consolidated analysis."""
    chains = [ReferenceChain(chain_str) for chain_str in chain_strings]
    
    all_leaked_classes = set()
    for chain in chains:
        for leak in chain.get_leak_nodes():
            all_leaked_classes.add(leak.class_name)
    
    result = {
        "total_chains": len(chains),
        "unique_leaked_classes": list(all_leaked_classes),
        "chains": [chain.to_dict() for chain in chains]
    }
    
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_chain.py <reference_chain> [<chain2>] [<chain3>] ...")
        print("\nExample:")
        print('  python parse_chain.py "IVShopItemTemplate:000000029E8DD9C0[true]._nameComp.IVTextQualityComponent:000000029E8D6300[false]"')
        sys.exit(1)
    
    chain_strings = sys.argv[1:]
    
    if len(chain_strings) == 1:
        # Single chain analysis
        chain = ReferenceChain(chain_strings[0])
        result = chain.to_dict()
    else:
        # Multiple chain analysis
        result = parse_multiple_chains(chain_strings)
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
