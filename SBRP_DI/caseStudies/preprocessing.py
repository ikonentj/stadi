
def makeScript(args, params, n_batches):
    case_id = args.case_id
    run_id  = args.run_id

    # load the template
    with open('scripts/execute.sh', 'r') as f:
        file = f.read()
    
    # fill the template
    file_edited = file.replace('<<<CASE>>>', str(case_id)).replace('<<<RUN>>>', str(run_id)).replace('<<<N_CPU>>>', str(params['threads'])).replace('<<<N_BATCHES>>>', str(n_batches-1))
    
    # save the script
    with open('bashexecute_{}_{}.sh'.format(case_id, run_id), 'w') as f:
        f.write(file_edited)

    print('If you are on a HPC, remember to mark the model to the slurm script: bashexecute_{}_{}.sh.'.format(case_id, run_id))