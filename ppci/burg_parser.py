#!/usr/bin/python
""" Automatically generated by xacc on Fri Sep 12 09:02:17 2014 """
from ppci.pyyacc import LRParser, Reduce, Shift, Accept, Production, Grammar
from ppci import Token


class Parser(LRParser):
    def __init__(self):
        self.start_symbol = "burgdef"
        self.grammar = Grammar({')', 'id', 'header', ':', '%%', ',', '(', 'string', 'number', '%terminal', ';'})
        self.grammar.add_production("burgdef", ['header', '%%', 'directives', '%%', 'rules'], self.action_burgdef_0)
        self.grammar.add_production("directives", [], self.action_directives_1)
        self.grammar.add_production("directives", ['directives', 'directive'], self.action_directives_2)
        self.grammar.add_production("directive", ['termdef'], self.action_directive_3)
        self.grammar.add_production("termdef", ['%terminal', 'termids'], self.action_termdef_4)
        self.grammar.add_production("termids", [], self.action_termids_5)
        self.grammar.add_production("termids", ['termids', 'termid'], self.action_termids_6)
        self.grammar.add_production("termid", ['id'], self.action_termid_7)
        self.grammar.add_production("rules", [], self.action_rules_8)
        self.grammar.add_production("rules", ['rules', 'rule'], self.action_rules_9)
        self.grammar.add_production("rule", ['id', ':', 'tree', 'cost', 'string'], self.action_rule_10)
        self.grammar.add_production("rule", ['id', ':', 'tree', 'cost', 'string', 'string'], self.action_rule_11)
        self.grammar.add_production("cost", ['number'], self.action_cost_12)
        self.grammar.add_production("tree", ['id'], self.action_tree_13)
        self.grammar.add_production("tree", ['id', '(', 'tree', ')'], self.action_tree_14)
        self.grammar.add_production("tree", ['id', '(', 'tree', ',', 'tree', ')'], self.action_tree_15)
        self.action_table = {}
        self.action_table[(21, ',')] = Shift(25)
        self.action_table[(37, ')')] = Reduce(14)
        self.action_table[(25, 'id')] = Shift(28)
        self.action_table[(4, '%%')] = Reduce(3)
        self.action_table[(16, 'number')] = Shift(19)
        self.action_table[(14, 'id')] = Shift(15)
        self.action_table[(13, 'id')] = Reduce(6)
        self.action_table[(12, '%%')] = Reduce(7)
        self.action_table[(9, '%%')] = Reduce(4)
        self.action_table[(7, '%%')] = Reduce(5)
        self.action_table[(20, ')')] = Reduce(13)
        self.action_table[(22, 'EOF')] = Reduce(10)
        self.action_table[(9, 'id')] = Shift(12)
        self.action_table[(12, '%terminal')] = Reduce(7)
        self.action_table[(18, 'string')] = Shift(22)
        self.action_table[(3, '%terminal')] = Shift(7)
        self.action_table[(33, 'number')] = Reduce(15)
        self.action_table[(36, ')')] = Reduce(15)
        self.action_table[(7, '%terminal')] = Reduce(5)
        self.action_table[(6, 'id')] = Reduce(8)
        self.action_table[(35, ',')] = Shift(38)
        self.action_table[(1, '%%')] = Shift(2)
        self.action_table[(2, '%%')] = Reduce(1)
        self.action_table[(20, '(')] = Shift(23)
        self.action_table[(36, ',')] = Reduce(15)
        self.action_table[(39, ')')] = Shift(40)
        self.action_table[(27, ')')] = Shift(30)
        self.action_table[(3, '%%')] = Shift(6)
        self.action_table[(29, ')')] = Shift(33)
        self.action_table[(35, ')')] = Shift(37)
        self.action_table[(13, '%terminal')] = Reduce(6)
        self.action_table[(31, 'id')] = Shift(28)
        self.action_table[(10, 'id')] = Reduce(9)
        self.action_table[(27, ',')] = Shift(31)
        self.action_table[(10, 'EOF')] = Reduce(9)
        self.action_table[(26, 'EOF')] = Reduce(11)
        self.action_table[(22, 'string')] = Shift(26)
        self.action_table[(8, 'EOF')] = Accept(0)
        self.action_table[(6, 'EOF')] = Reduce(8)
        self.action_table[(15, '(')] = Shift(17)
        self.action_table[(9, '%terminal')] = Reduce(4)
        self.action_table[(28, '(')] = Shift(32)
        self.action_table[(32, 'id')] = Shift(20)
        self.action_table[(2, '%terminal')] = Reduce(1)
        self.action_table[(4, '%terminal')] = Reduce(3)
        self.action_table[(22, 'id')] = Reduce(10)
        self.action_table[(26, 'id')] = Reduce(11)
        self.action_table[(23, 'id')] = Shift(20)
        self.action_table[(11, ':')] = Shift(14)
        self.action_table[(28, ')')] = Reduce(13)
        self.action_table[(17, 'id')] = Shift(20)
        self.action_table[(15, 'number')] = Reduce(13)
        self.action_table[(19, 'string')] = Reduce(12)
        self.action_table[(38, 'id')] = Shift(28)
        self.action_table[(30, ',')] = Reduce(14)
        self.action_table[(7, 'id')] = Reduce(5)
        self.action_table[(20, ',')] = Reduce(13)
        self.action_table[(12, 'id')] = Reduce(7)
        self.action_table[(13, '%%')] = Reduce(6)
        self.action_table[(21, ')')] = Shift(24)
        self.action_table[(30, ')')] = Reduce(14)
        self.action_table[(5, '%%')] = Reduce(2)
        self.action_table[(5, '%terminal')] = Reduce(2)
        self.action_table[(8, 'id')] = Shift(11)
        self.action_table[(34, ')')] = Shift(36)
        self.action_table[(40, ')')] = Reduce(15)
        self.action_table[(24, 'number')] = Reduce(14)
        self.action_table[(0, 'header')] = Shift(1)

        self.goto_table = {}
        self.goto_table[(3, 'termdef')] = 4
        self.goto_table[(16, 'cost')] = 18
        self.goto_table[(32, 'tree')] = 35
        self.goto_table[(31, 'tree')] = 34
        self.goto_table[(9, 'termid')] = 13
        self.goto_table[(6, 'rules')] = 8
        self.goto_table[(7, 'termids')] = 9
        self.goto_table[(23, 'tree')] = 27
        self.goto_table[(3, 'directive')] = 5
        self.goto_table[(25, 'tree')] = 29
        self.goto_table[(8, 'rule')] = 10
        self.goto_table[(14, 'tree')] = 16
        self.goto_table[(2, 'directives')] = 3
        self.goto_table[(17, 'tree')] = 21
        self.goto_table[(38, 'tree')] = 39

    def action_burgdef_0(self, arg1, arg2, arg3, arg4, arg5):
        self.system.header_lines = arg1.val

    def action_directives_1(self):
        pass

    def action_directives_2(self, arg1, arg2):
        pass

    def action_directive_3(self, arg1):
        pass

    def action_termdef_4(self, arg1, arg2):
        pass

    def action_termids_5(self):
        pass

    def action_termids_6(self, arg1, arg2):
        pass

    def action_termid_7(self, arg1):
        self.system.add_terminal(arg1.val)

    def action_rules_8(self):
        pass

    def action_rules_9(self, arg1, arg2):
        pass

    def action_rule_10(self, arg1, arg2, arg3, arg4, arg5):
        self.system.add_rule(arg1.val, arg3, arg4, None, arg5.val)

    def action_rule_11(self, arg1, arg2, arg3, arg4, arg5, arg6):
        self.system.add_rule(arg1.val, arg3, arg4, arg5.val, arg6.val)

    def action_cost_12(self, arg1):
        return arg1.val

    def action_tree_13(self, arg1):
        return self.system.tree(arg1.val)

    def action_tree_14(self, arg1, arg2, arg3, arg4):
        return self.system.tree(arg1.val, arg3)

    def action_tree_15(self, arg1, arg2, arg3, arg4, arg5, arg6):
        return self.system.tree(arg1.val, arg3, arg5)
