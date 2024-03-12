$(function() {
    new DataTable('#table-task-runs', {
        ajax: {
            url: `/api/task/${TASK_ID}/runs`,
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            // TODO: Заполнить title
            { data: 'id', title: 'id', },
            { data: 'task', title: 'task', },
            { data: 'command', title: 'Команда', },
            { data: 'status', title: 'Статус', },
            { data: 'process_id', title: 'process_id', },
            { data: 'process_return_code', title: 'process_return_code', },
            { data: 'create_date', title: 'create_date', },
            { data: 'start_date', title: 'start_date', },
            { data: 'finish_date', title: 'finish_date', },
            { data: 'scheduled_date', title: 'scheduled_date', },
        ]
    });
});
