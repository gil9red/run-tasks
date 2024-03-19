function kind_render(data, type, row, meta) {
    if (type === 'filter') {
        return data;
    }

    let icon = data;
    switch (data) {
        case "email":
            icon = `<i class="bi bi-envelope-fill"></i>`;
            break;

        case "telegram":
            icon = `<i class="bi bi-telegram"></i>`;
            break;
    }
    return `<div class="d-flex justify-content-center">${icon}</div>`;
}


// TODO: Общий код для функций обновления таблиц
function get_table() {
    return $("#table-notifications").DataTable();
}


function get_table_row_by_id(id) {
    return get_table().row("#" + id);
}


function process_table_rows_from_response(rs, callback) {
    let ok = rs.status == 'ok';

    if (ok && rs.result != null) {
        for (let obj of rs.result) {
            let row = get_table_row_by_id(obj.id);
            callback(obj, row);
        }
    }
}


function update_rows_table_by_response(rs) {
    process_table_rows_from_response(
        rs,
        (obj, row) => {
            let is_exist = row.any();
            if (is_exist) {
                row.data(obj).draw("full-hold"); // full-hold сохраняет пагинацию
            } else {
                row.table().row.add(obj).draw(); // Тут пагинация вернется к первой странице
            }
        }
    );
}


$(function() {
    // Создание уведомления
    let $modal_create_notification = $('#modal-create-notification');

    $modal_create_notification.find("form").submit(function() {
        $modal_create_notification.modal('hide');

        let thisForm = this;

        let url = $(this).attr("action");
        let method = $(this).attr("method");
        if (method === undefined) {
            method = "get";
        }

        $.ajax({
            url: url,
            method: method,  // HTTP метод, по умолчанию GET
            data: JSON.stringify(convertFormToJSON(this)),
            contentType: "application/json; charset=utf-8",
            dataType: "json",  // Тип данных загружаемых с сервера
            success: function(data) {
                on_ajax_success(data, update_rows_table_by_response);

                // Очищение полей формы
                thisForm.reset();
            },
            error: data => on_ajax_error(data, 'при создании уведомления'),
        });

        return false;
    });

    new DataTable('#table-notifications', {
        ajax: {
            url: `/api/notifications`,
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            { data: 'id', title: 'Ид.', }, // TODO: Спрятать?
            { data: 'task_run', title: 'Ид. запуска', }, // TODO: Спрятать? Заполнять ссылку на запуск (брать task_run_seq)?
            { data: 'name', title: 'Название', },
            { data: 'text', title: 'Текст', },
            { data: 'kind', title: 'Тип', render: kind_render, },
            { data: 'append_date', title: 'Добавлено', render: date_render, },
            { data: 'sending_date', title: 'Отправлено', render: date_render, },
        ],
        order: [
            // Сортировка по убыванию id
            [0, "desc"],
        ],
        language: LANG_DATATABLES,
    });
});
