"""Read-only project status; excludes source text, prompts and private ledgers."""
from research.workflow import Workflow, STAGES


def payload(repository):
    result=[]
    for path in sorted((repository.root/'output').glob('framework_*/workflow.json')):
        try:
            directory=repository._safe(path.parent)
            workflow=Workflow(directory)
            workflow.verify()
            status=workflow.status()
            topic=workflow.artifact('topic')['payload']['topic']
            artifacts=[]
            for stage in STAGES:
                row=workflow.state['stages'][stage]
                artifacts.append({'stage':stage,'status':row['status'],'attempts':row['attempts'],
                                  'sha256':row.get('sha256')})
            implementation=(workflow.artifact('implementation')['payload']
                            if workflow.state['stages']['implementation']['status']=='completed' else {})
            release=(workflow.artifact('export')['payload'].get('delivery',{})
                     if workflow.state['stages']['export']['status']=='completed' else {})
            result.append({'directory':directory.name,'topic':topic,**status,'artifacts':artifacts,
                           'generated_method':bool(implementation.get('source_path')),
                           'methods':implementation.get('capabilities',[]),
                           'release':{k:release.get(k) for k in ('file_count','external_review_ready','visual_review_ready')},
                           'feedback_count':len(workflow.state['feedback']),
                           'last_event':workflow.state['events'][-1]['event'] if workflow.state['events'] else None})
        except (ValueError,KeyError,TypeError,OSError):
            result.append({'directory':path.parent.name,'topic':'项目产物需要核对','status':'invalid','stages':{}})
    return result
