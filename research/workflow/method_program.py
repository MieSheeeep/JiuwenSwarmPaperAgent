"""Bounded interpreter for generated Python selection methods; never exec/eval."""
import ast
import operator

class MethodError(ValueError):
    pass


class Program:
    """Supported function: select(question, passages, budget) -> passage ID list."""
    def __init__(self, source):
        if not isinstance(source,str) or len(source)>20000:raise MethodError('Source size limit')
        self.source=source
        self.tree=ast.parse(source)
        if len(self.tree.body)!=1 or not isinstance(self.tree.body[0],ast.FunctionDef):
            raise MethodError('One select function required')
        function=self.tree.body[0]
        if (function.name!='select' or [a.arg for a in function.args.args]!=['question','passages','budget']
                or function.decorator_list or function.args.defaults or function.args.vararg or function.args.kwarg
                or function.args.posonlyargs or function.args.kwonlyargs):
            raise MethodError('Expected select(question, passages, budget)')
        allowed=(ast.Module,ast.FunctionDef,ast.arguments,ast.arg,ast.Assign,ast.Return,ast.If,ast.For,
                 ast.Expr,ast.Name,ast.Constant,ast.List,ast.Tuple,ast.Dict,ast.Set,ast.Load,ast.Store,
                 ast.Subscript,ast.Slice,ast.Call,ast.Attribute,ast.keyword,ast.Lambda,
                 ast.ListComp,ast.SetComp,ast.GeneratorExp,ast.comprehension,ast.Compare,ast.BoolOp,
                 ast.UnaryOp,ast.BinOp,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.BitAnd,ast.BitOr,ast.USub,ast.Not,ast.And,ast.Or,
                 ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.In,ast.NotIn,ast.IfExp)
        for node in ast.walk(function):
            if not isinstance(node,allowed):raise MethodError('Unsupported syntax: '+type(node).__name__)
            if isinstance(node,ast.Attribute) and node.attr not in ('lower','split','count','get','append','intersection','union','add'):
                raise MethodError('Unsupported attribute: '+node.attr)
            if isinstance(node,ast.Name) and node.id.startswith('_'):raise MethodError('Private names forbidden')
        self.body=function.body

    def tick(self):
        self.fuel-=1
        if self.fuel<0:raise MethodError('Operation limit reached')

    def sequence(self,value):
        if not isinstance(value,(list,tuple,set,dict,str)) or len(value)>50000:
            raise MethodError('Bounded sequence required')
        return value

    def expression(self,node,env):
        self.tick()
        if isinstance(node,ast.Constant):
            if not isinstance(node.value,(str,int,float,bool,type(None))):raise MethodError('Constant type')
            if isinstance(node.value,str) and len(node.value)>2000:raise MethodError('Constant size')
            return node.value
        if isinstance(node,ast.Name):
            if node.id not in env:raise MethodError('Unknown variable: '+node.id)
            return env[node.id]
        if isinstance(node,(ast.List,ast.Tuple,ast.Set)):
            values=[self.expression(e,env) for e in node.elts]
            return set(values) if isinstance(node,ast.Set) else values
        if isinstance(node,ast.Dict):
            if any(k is None for k in node.keys):raise MethodError('No dictionary unpacking')
            return {self.expression(k,env):self.expression(v,env) for k,v in zip(node.keys,node.values)}
        if isinstance(node,ast.Subscript):
            return self.expression(node.value,env)[self.expression(node.slice,env)]
        if isinstance(node,ast.Slice):
            return slice(*(self.expression(x,env) if x else None for x in (node.lower,node.upper,node.step)))
        if isinstance(node,ast.BinOp):
            a,b=self.expression(node.left,env),self.expression(node.right,env)
            if isinstance(node.op,ast.Mult) and (isinstance(a,int) and abs(a)>1000 or isinstance(b,int) and abs(b)>1000):
                raise MethodError('Multiplication bound')
            fn={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,
                ast.BitAnd:operator.and_,ast.BitOr:operator.or_}[type(node.op)]
            value=fn(a,b)
            if isinstance(value,(str,list)) and len(value)>50000:raise MethodError('Value size bound')
            return value
        if isinstance(node,ast.UnaryOp):
            value=self.expression(node.operand,env)
            return not value if isinstance(node.op,ast.Not) else -value
        if isinstance(node,ast.BoolOp):
            value=None
            for part in node.values:
                value=self.expression(part,env)
                if isinstance(node.op,ast.And) and not value or isinstance(node.op,ast.Or) and value:return value
            return value
        if isinstance(node,ast.Compare):
            left=self.expression(node.left,env)
            ops={ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Lt:operator.lt,ast.LtE:operator.le,
                 ast.Gt:operator.gt,ast.GtE:operator.ge,ast.In:lambda a,b:a in b,ast.NotIn:lambda a,b:a not in b}
            for op,right_node in zip(node.ops,node.comparators):
                right=self.expression(right_node,env)
                if not ops[type(op)](left,right):return False
                left=right
            return True
        if isinstance(node,ast.IfExp):
            return self.expression(node.body if self.expression(node.test,env) else node.orelse,env)
        if isinstance(node,ast.Lambda):
            names=[a.arg for a in node.args.args]
            return lambda *args:self.expression(node.body,{**env,**dict(zip(names,args))})
        if isinstance(node,(ast.ListComp,ast.SetComp,ast.GeneratorExp)):
            if len(node.generators)!=1:raise MethodError('One bounded comprehension allowed')
            gen=node.generators[0]
            if not isinstance(gen.target,ast.Name) or gen.is_async:raise MethodError('Comprehension target')
            values=[]
            for item in self.sequence(self.expression(gen.iter,env)):
                local={**env,gen.target.id:item}
                if all(self.expression(x,local) for x in gen.ifs):values.append(self.expression(node.elt,local))
            return set(values) if isinstance(node,ast.SetComp) else values
        if isinstance(node,ast.Call):
            args=[self.expression(a,env) for a in node.args]
            kwargs={k.arg:self.expression(k.value,env) for k in node.keywords}
            if None in kwargs:raise MethodError('No keyword unpacking')
            if isinstance(node.func,ast.Name):
                name=node.func.id
                functions={'len':len,'set':set,'list':list,'str':str,'min':min,'max':max,'sum':sum,'sorted':sorted}
                if name not in functions:raise MethodError('Unsupported call')
                if name in ('set','list','sum','sorted') and args:self.sequence(args[0])
                return functions[name](*args,**kwargs)
            if isinstance(node.func,ast.Attribute):
                value=self.expression(node.func.value,env);name=node.func.attr
                permitted=((isinstance(value,str) and name in ('lower','split','count')) or
                    isinstance(value,dict) and name=='get' or isinstance(value,list) and name=='append' or
                    isinstance(value,set) and name in ('intersection','union','add'))
                if not permitted:raise MethodError('Method receiver mismatch')
                if name in ('append','add') and len(value)>=500:raise MethodError('Collection size limit')
                result=getattr(value,name)(*args,**kwargs)
                if isinstance(result,list) and len(result)>50000:raise MethodError('List size limit')
                return result
            raise MethodError('Indirect calls forbidden')
        raise MethodError('Unsupported expression')

    def statements(self,body,env):
        for node in body:
            self.tick()
            if isinstance(node,ast.Return):return True,self.expression(node.value,env)
            if isinstance(node,ast.Assign):
                if len(node.targets)!=1 or not isinstance(node.targets[0],ast.Name):raise MethodError('Simple assignment required')
                env[node.targets[0].id]=self.expression(node.value,env)
            elif isinstance(node,ast.Expr):self.expression(node.value,env)
            elif isinstance(node,ast.If):
                done,value=self.statements(node.body if self.expression(node.test,env) else node.orelse,env)
                if done:return done,value
            elif isinstance(node,ast.For):
                if node.orelse:raise MethodError('Simple for required')
                for item in self.sequence(self.expression(node.iter,env)):
                    if isinstance(node.target,ast.Name):env[node.target.id]=item
                    elif isinstance(node.target,ast.Tuple) and all(isinstance(n,ast.Name) for n in node.target.elts):
                        if not isinstance(item,(tuple,list)) or len(item)!=len(node.target.elts):
                            raise MethodError('Unpacking shape mismatch')
                        for name,value in zip(node.target.elts,item):env[name.id]=value
                    else:raise MethodError('Simple for target required')
                    done,value=self.statements(node.body,env)
                    if done:return done,value
            else:raise MethodError('Unsupported statement')
        return False,None

    def select(self,question,passages,budget):
        self.fuel=100000
        # Only public data is projected into the interpreter.
        docs=[{k:p[k] for k in ('id','title','text')} for p in passages]
        if len(docs)>100 or sum(len(p['text']) for p in docs)>100000:raise MethodError('Input size limit')
        if type(budget) is not int or not 1<=budget<=100:raise MethodError('Budget limit')
        _,value=self.statements(self.body,{'question':question,'passages':docs,'budget':budget})
        if not isinstance(value,list) or len(value)>budget or any(not isinstance(v,str) for v in value):
            raise MethodError('Return at most budget passage IDs')
        if len(set(value))!=len(value) or not set(value)<={p['id'] for p in docs}:raise MethodError('Unknown or duplicate IDs')
        return value
