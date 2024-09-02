$.noty.defaults.theme = 'defaultTheme';
$.noty.defaults.layout = 'bottomRight';
$.noty.defaults.timeout = 10000; // 10 secs
$.noty.defaults.progressBar = true;


// NOTE: https://stackoverflow.com/a/69718380/5909792
String.prototype.format = function () {
    let args = arguments;
    return this.replace(/{([0-9]+)}/g, function (match, index) {
        // check if the argument is there
        return typeof args[index] == 'undefined' ? match : args[index];
    });
};


LANG_DATATABLES = {
    "processing": "Подождите...",
    "search": "Поиск:",
    "lengthMenu": "Показать _MENU_ записей",
    "info": "Записи с _START_ до _END_ из _TOTAL_ записей",
    "infoEmpty": "Записи с 0 до 0 из 0 записей",
    "infoFiltered": "(отфильтровано из _MAX_ записей)",
    "loadingRecords": "Загрузка записей...",
    "zeroRecords": "Записи отсутствуют.",
    "emptyTable": "В таблице отсутствуют данные",
    "aria": {
        "sortAscending": ": активировать для сортировки столбца по возрастанию",
        "sortDescending": ": активировать для сортировки столбца по убыванию"
    },
    "select": {
        "rows": {
            "_": "Выбрано записей: %d",
            "1": "Выбрана одна запись"
        },
        "cells": {
            "_": "Выбрано %d ячеек",
            "1": "Выбрана 1 ячейка "
        },
        "columns": {
            "1": "Выбран 1 столбец ",
            "_": "Выбрано %d столбцов "
        }
    },
    "searchBuilder": {
        "conditions": {
            "string": {
                "startsWith": "Начинается с",
                "contains": "Содержит",
                "empty": "Пусто",
                "endsWith": "Заканчивается на",
                "equals": "Равно",
                "not": "Не",
                "notEmpty": "Не пусто",
                "notContains": "Не содержит",
                "notStartsWith": "Не начинается на",
                "notEndsWith": "Не заканчивается на"
            },
            "date": {
                "after": "После",
                "before": "До",
                "between": "Между",
                "empty": "Пусто",
                "equals": "Равно",
                "not": "Не",
                "notBetween": "Не между",
                "notEmpty": "Не пусто"
            },
            "number": {
                "empty": "Пусто",
                "equals": "Равно",
                "gt": "Больше чем",
                "gte": "Больше, чем равно",
                "lt": "Меньше чем",
                "lte": "Меньше, чем равно",
                "not": "Не",
                "notEmpty": "Не пусто",
                "between": "Между",
                "notBetween": "Не между ними"
            },
            "array": {
                "equals": "Равно",
                "empty": "Пусто",
                "contains": "Содержит",
                "not": "Не равно",
                "notEmpty": "Не пусто",
                "without": "Без"
            }
        },
        "data": "Данные",
        "deleteTitle": "Удалить условие фильтрации",
        "logicAnd": "И",
        "logicOr": "Или",
        "title": {
            "0": "Конструктор поиска",
            "_": "Конструктор поиска (%d)"
        },
        "value": "Значение",
        "add": "Добавить условие",
        "button": {
            "0": "Конструктор поиска",
            "_": "Конструктор поиска (%d)"
        },
        "clearAll": "Очистить всё",
        "condition": "Условие",
        "leftTitle": "Превосходные критерии",
        "rightTitle": "Критерии отступа"
    },
    "searchPanes": {
        "clearMessage": "Очистить всё",
        "collapse": {
            "0": "Панели поиска",
            "_": "Панели поиска (%d)"
        },
        "count": "{total}",
        "countFiltered": "{shown} ({total})",
        "emptyPanes": "Нет панелей поиска",
        "loadMessage": "Загрузка панелей поиска",
        "title": "Фильтры активны - %d",
        "showMessage": "Показать все",
        "collapseMessage": "Скрыть все"
    },
    "buttons": {
        "pdf": "PDF",
        "print": "Печать",
        "collection": "Коллекция <span class=\"ui-button-icon-primary ui-icon ui-icon-triangle-1-s\"><\/span>",
        "colvis": "Видимость столбцов",
        "colvisRestore": "Восстановить видимость",
        "copy": "Копировать",
        "copyTitle": "Скопировать в буфер обмена",
        "csv": "CSV",
        "excel": "Excel",
        "pageLength": {
            "-1": "Показать все строки",
            "_": "Показать %d строк",
            "1": "Показать 1 строку"
        },
        "removeState": "Удалить",
        "renameState": "Переименовать",
        "copySuccess": {
            "1": "Строка скопирована в буфер обмена",
            "_": "Скопировано %d строк в буфер обмена"
        },
        "createState": "Создать состояние",
        "removeAllStates": "Удалить все состояния",
        "savedStates": "Сохраненные состояния",
        "stateRestore": "Состояние %d",
        "updateState": "Обновить",
        "copyKeys": "Нажмите ctrl  или u2318 + C, чтобы скопировать данные таблицы в буфер обмена.  Для отмены, щелкните по сообщению или нажмите escape."
    },
    "decimal": ".",
    "infoThousands": ",",
    "autoFill": {
        "cancel": "Отменить",
        "fill": "Заполнить все ячейки <i>%d<i><\/i><\/i>",
        "fillHorizontal": "Заполнить ячейки по горизонтали",
        "fillVertical": "Заполнить ячейки по вертикали",
        "info": "Информация"
    },
    "datetime": {
        "previous": "Предыдущий",
        "next": "Следующий",
        "hours": "Часы",
        "minutes": "Минуты",
        "seconds": "Секунды",
        "unknown": "Неизвестный",
        "amPm": [
            "AM",
            "PM"
        ],
        "months": {
            "0": "Январь",
            "1": "Февраль",
            "10": "Ноябрь",
            "11": "Декабрь",
            "2": "Март",
            "3": "Апрель",
            "4": "Май",
            "5": "Июнь",
            "6": "Июль",
            "7": "Август",
            "8": "Сентябрь",
            "9": "Октябрь"
        },
        "weekdays": [
            "Вс",
            "Пн",
            "Вт",
            "Ср",
            "Чт",
            "Пт",
            "Сб"
        ]
    },
    "editor": {
        "close": "Закрыть",
        "create": {
            "button": "Новый",
            "title": "Создать новую запись",
            "submit": "Создать"
        },
        "edit": {
            "button": "Изменить",
            "title": "Изменить запись",
            "submit": "Изменить"
        },
        "remove": {
            "button": "Удалить",
            "title": "Удалить",
            "submit": "Удалить",
            "confirm": {
                "_": "Вы точно хотите удалить %d строк?",
                "1": "Вы точно хотите удалить 1 строку?"
            }
        },
        "multi": {
            "restore": "Отменить изменения",
            "title": "Несколько значений",
            "info": "Выбранные элементы содержат разные значения для этого входа. Чтобы отредактировать и установить для всех элементов этого ввода одинаковое значение, нажмите или коснитесь здесь, в противном случае они сохранят свои индивидуальные значения.",
            "noMulti": "Это поле должно редактироваться отдельно, а не как часть группы"
        },
        "error": {
            "system": "Возникла системная ошибка (<a target=\"\\\" rel=\"nofollow\" href=\"\\\">Подробнее<\/a>)."
        }
    },
    "searchPlaceholder": "Что ищете?",
    "stateRestore": {
        "creationModal": {
            "button": "Создать",
            "search": "Поиск",
            "columns": {
                "search": "Поиск по столбцам",
                "visible": "Видимость столбцов"
            },
            "name": "Имя:",
            "order": "Сортировка",
            "paging": "Страницы",
            "scroller": "Позиция прокрутки",
            "searchBuilder": "Редактор поиска",
            "select": "Выделение",
            "title": "Создать новое состояние",
            "toggleLabel": "Включает:"
        },
        "removeJoiner": "и",
        "removeSubmit": "Удалить",
        "renameButton": "Переименовать",
        "duplicateError": "Состояние с таким именем уже существует.",
        "emptyError": "Имя не может быть пустым.",
        "emptyStates": "Нет сохраненных состояний",
        "removeConfirm": "Вы уверены, что хотите удалить %s?",
        "removeError": "Не удалось удалить состояние.",
        "removeTitle": "Удалить состояние",
        "renameLabel": "Новое имя для %s:",
        "renameTitle": "Переименовать состояние"
    },
    "thousands": " "
}


function tableInitComplete(settings, json) {
    let api = this.api();

    setInterval(
        function () {
            // Пользовательская пагинация не сбрасывается при обновлении
            api.ajax.reload(null, false);
        },
        5000 // Каждые 5 секунд
    );
}


function get_state_key(settings) {
    // Стандартный ключ DataTable подразумеваем адрес, а он будет свой для задач и запусков
    // Поэтому, его делать только от ид таблиц, но, тогда, ид таблиц должен быть уникальным
    // среди всех страниц
    return `DataTables_${settings.sInstance}`;
}


COMMON_PROPS_DATA_TABLE = {
    stateSave: true,
    stateDuration: 0, // Без ограничения срока хранения
    stateSaveCallback: function (settings, data) {
        const key = get_state_key(settings);

        if (data.custom_columns_visible == null) {
            data.custom_columns_visible = {};
        }

        const api = new DataTable.Api(settings);
        for (let aoColumn of api.context[0].aoColumns) {
            let dataSrc = aoColumn.data;
            if (dataSrc == null) {
                continue;
            }

            data.custom_columns_visible[dataSrc] = aoColumn.bVisible;
        }

        localStorage.setItem(key, JSON.stringify(data));
    },
    stateLoadCallback: function (settings) {
        const key = get_state_key(settings);

        let data = JSON.parse(localStorage.getItem(key));
        if (data == null) {
            data = {};
        }
        if (data.custom_columns_visible == null) {
            data.custom_columns_visible = {};
        }

        // NOTE: На текущий момент #table-visible-columns не существует
        //       Продолжение работы в preInit.dt
        settings.custom_columns_visible = data.custom_columns_visible;

        return data;
    },
    initComplete: tableInitComplete,
    language: LANG_DATATABLES,
}


function get_date_from_utc(utc) {
    if (utc == null) {
        return null;
    }
    return moment.utc(utc).format("DD/MM/YYYY HH:mm:ss");
}


function fill_document_fields(obj) {
    for (let [field, value] of Object.entries(obj)) {
        let tag = document.getElementById(field);
        if (tag == null) {
            continue;
        }

        // Наличие атрибута data-is-utc для полей-дат
        if (tag.dataset.isUtc) {
            value = get_date_from_utc(value);
        }

        switch (tag.tagName) {
            case "INPUT": {
                switch (tag.getAttribute("type")) {
                    case "checkbox": {
                        tag.checked = value;
                        break;
                    }
                    default: { // text
                        tag.value = value;
                    }
                }
                break;
            }
            case "TEXTAREA": {
                tag.value = value;
                break;
            }
            case "DIV": {
                tag.innerHTML = value;
                break;
            }
            default: {
                console.error(`Unsupported tag ${tag.tagName}`);
            }
        }
    }
}


function date_render(data, type, row, meta) {
    if (data == null) {
        return data;
    }
    if (type === 'display' || type === 'filter') {
        return get_date_from_utc(data);
    }
    return data;
}


function bool_render(data, type, row, meta) {
    if (type === 'filter') {
        return data;
    }
    if (type === 'sort') {
        // Сортировка по bool не работает
        return data.toString();
    }
    return `
        <div class="form-check form-switch d-flex justify-content-center">
            <input
                    class="form-check-input"
                    type="checkbox"
                    role="switch"
                    data-context-obj-id="${row.id}"
                    data-context-obj-field="${meta.settings.aoColumns[meta.col].data}"
                    data-context-table-id="#${meta.settings.sTableId}"
                    ${data ? "checked" : ""}
            />
        </div>
    `;
}


function get_work_status_task_widget(data, showTitle=false, spinnerSize=2) {
    let title = data;
    let result = `<span class="text-bg-danger">${data}</span>`;

    switch (data) {
        case "none": {
            title = "Не было запусков";
            result = `
                <span class="text-secondary-emphasis" title="${title}">
                    <i class="bi bi-slash-circle"></i>
                </span>
            `;
            break;
        }

        case "in_processed": {
            title = "Выполняется запуск";
            result = `
                <span
                        class="spinner-grow text-primary"
                        role="status"
                        title="${title}"
                        style="width: ${spinnerSize}rem; height: ${spinnerSize}rem;"
                >
                    <span class="visually-hidden">Выполняется запуск...</span>
                </span>
            `;
            break;
        }

        case "successful": {
            title = "Последний запуск завершился успешно";
            result = `
                <span class="text-success" title="${title}">
                    <i class="bi bi-check-circle"></i>
                </span>
            `;
            break;
        }

        case "failed": {
            title = "Последний запуск завершился ошибкой";
            result = `
                <span class="text-danger" title="${title}">
                    <i class="bi bi-x-circle"></i>
                </span>
            `;
            break;
        }

        case "stopped": {
            title = "Последний запуск был остановлен";
            result = `
                <span class="text-warning" title="${title}">
                    <i class="bi bi-stop-circle"></i>
                </span>
            `;
            break;
        }
    }

    if (showTitle) {
        result = `${result}<span class="fs-3"> — ${title}</span>`;
    }

    return result;
}


function work_status_task_run_render(data, type, row, meta) {
    if (type === 'filter') {
        return null;
    }

    let result = get_work_status_task_widget(
        data,
        false, // showTitle
        1      // spinnerSize
    );
    return `
        <div class="d-flex justify-content-center">
            ${result}
        </div>
    `;
}


function delete_table_row(css_selector_table, row_id) {
    let table = $(css_selector_table).DataTable();
    let row = table.row("#" + row_id);
    row.remove().draw();
}


function update_rows_table_by_response(css_selector_table, rs) {
    if (css_selector_table == null) {
        return;
    }

    let ok = rs.status == 'ok';
    if (ok && rs.result != null) {
        let table = $(css_selector_table).DataTable();

        for (let obj of rs.result) {
            let row = table.row("#" + obj.id);
            let is_exist = row.any();
            if (is_exist) {
                row.data(obj).draw("full-hold"); // full-hold сохраняет пагинацию
            } else {
                row.table().row.add(obj).draw(); // Тут пагинация вернется к первой странице
            }
        }
    }
}


function go_to_login_url() {
    // Если сейчас страница логина
    if (window.location.pathname.includes("/login")) {
        return;
    }

    window.location = `${window.location.origin}/login?from=${window.location.pathname}`;
}


// SOURCE: https://stackoverflow.com/a/48332750/5909792
$.fn.dataTable.ext.errMode = function (settings, tn, msg) {
    // Редирект на страницу логина
    if (settings && settings.jqXHR && settings.jqXHR.status == 401) {
        console.log("Статус ответа 401 unauthorized");

        go_to_login_url();
        return;
    }
    alert(msg); // Alert for all other error types
};


function on_ajax_success(rs, css_selector_table=null, callback=null) {
    let ok = rs.status == 'ok';
    if (rs.text) {
        noty({
            text: rs.text,
            type: ok ? 'success' : 'warning',
        });
    }

    if (callback != null) {
        callback(css_selector_table, rs);
    }
}


function on_ajax_error(rs, reason) {
    // Редирект на страницу логина
    if (rs.status == 401) {
        console.log("Статус ответа 401 unauthorized");

        go_to_login_url();
        return;
    }

    let text = "На сервере произошла неожиданная ошибка";
    if (rs.responseJSON && rs.responseJSON.text) {
        text = `${text}: ${rs.responseJSON.text}`;
    }
    noty({
        text: reason ? `${text} ${reason}` : text,
        type: 'error',
    });
}


function send_ajax(url, method, json=null, css_selector_table=null, callback=null) {
    $.ajax({
        url: url,
        method: method,
        data: json ? JSON.stringify(json) : null,
        contentType: "application/json; charset=utf-8",
        dataType: "json",  // Тип данных загружаемых с сервера
        success: data => on_ajax_success(data, css_selector_table, callback),
        error: data => on_ajax_error(data), // TODO: заполнять reason в on_ajax_error
    });
}


function get_column_by_data_src(api, data_src) {
    if (data_src == null) {
        return null;
    }

    for (let i = 0; i < api.context[0].aoColumns.length; i++) {
        if (data_src == api.column(i).dataSrc()) {
            return api.column(i);
        }
    }

    return null;
}


function table_set_visible_column(api, dataSrc, value) {
    // TODO: Надо ли пересчитывать размеры таблицы? Если заголовков мало, то странно выглядит
    let column = get_column_by_data_src(api, dataSrc);
    if (column != null) {
        column.visible(value);
    }
}


function getTableHeaderTitleWithMenu(appendActions=[]) {
    return `
        <div>
            <button class="btn btn-secondary btn-sm" type="button" data-bs-toggle="dropdown" data-bs-auto-close="outside" aria-expanded="false">
                <i class="bi bi-list"></i>
            </button>
            <ul class="dropdown-menu">
                ${appendActions.length ? appendActions.join("") + '<li><hr class="dropdown-divider"></li>' : ''}
                <li>
                    <div class="dropdown dropend">
                        <a
                                class="dropdown-item dropdown-toggle icon-link icon-link-hover"
                                href="#"
                                id="dropdown-layouts"
                                data-bs-toggle="dropdown"
                                data-bs-auto-close="outside"
                                aria-haspopup="true"
                                aria-expanded="false"
                        >
                            <i class="bi bi-eye-slash"></i>
                            Видимость столбцов
                        </a>
                        <div id="table-visible-columns" class="dropdown-menu" aria-labelledby="dropdown-layouts">
                            <!-- Заполнение из js -->
                        </div>
                    </div>
                </li>
            </ul>
        </div>
    `;
}


function check_notifications_get_number_of_unsent() {
    send_ajax(
        "/api/notifications/get-number-of-unsent",
        "GET",
        null, // json
        null, // css_selector_table
        (css_selector_table, rs) => {
            let number = rs.result[0].number;

            let $el = $("#unsent-notifications");
            $el.text(number);
            $el.toggleClass("d-none", number == 0);
        }
    );
}


$(function() {
    $(document).on('preInit.dt', function (e, settings) {
        let $table_visible_columns = $("#table-visible-columns");
        if ($table_visible_columns.length) {
            const column_class = "column-visible";

            let items = [];

            const api = new DataTable.Api(settings);
            const context = api.context[0];
            for (let aoColumn of context.aoColumns) {
                let dataSrc = aoColumn.data;
                if (dataSrc == null) {
                    continue;
                }

                let id_of_column = `cb_visible_column_${dataSrc}`;
                let is_visible = settings.custom_columns_visible[dataSrc];
                if (is_visible == null) {
                    is_visible = aoColumn.bVisible;
                }
                items.push(`
                    <div class="dropdown-item">
                        <div class="form-check">
                            <input
                                    class="form-check-input ${column_class}"
                                    type="checkbox"
                                    id="${id_of_column}"
                                    data-context-table-id="#${context.sTableId}"
                                    data-context-table-column-data-src="${dataSrc}"
                                    ${is_visible ? "checked" : ""}
                            >
                            <label class="form-check-label w-100" for="${id_of_column}">
                                ${aoColumn.title}
                            </label>
                        </div>
                    </div>
                `);
            }
            $table_visible_columns.html(
                items.join("")
            );

            // Прокидывание клика на чекбокс
            $(`.dropdown-item:has(.${column_class})`).on('click', function (e) {
                $(this).find(`.${column_class}`).trigger("click");
            });

            $(`.${column_class}`).on('change', function (e) {
                let $this = $(this);
                let dataSrc = $this.data('context-table-column-data-src');
                let value = $this.prop('checked');

                table_set_visible_column(api, dataSrc, value);
            });
        }
    });

    if ($("#unsent-notifications").length) {
        check_notifications_get_number_of_unsent();
        setInterval(
            check_notifications_get_number_of_unsent,
            5000 // Каждые 5 секунд
        );
    }
});


$(document).on("click", "[data-url]", function() {
    let $this = $(this);

    let confirm_text = $this.data("confirm-text");
    if (confirm_text != null && !window.confirm(confirm_text)) {
        return;
    }

    send_ajax(
        $this.data("url"),
        $this.data("method")
    );

    let callback = $this.data("callback");
    if (callback != null) {
        eval(callback);
    }
});


function get_context_obj_field($this) {
    let field = $this.data("context-obj-field");

    let obj = new Object();
    obj[field] = $this.is(':checked');

    return obj;
}


function get_url_update($src_url_update, $this) {
    return $src_url_update.data("url-update")
        .replace("{context_obj_id}", $this.data("context-obj-id"))
    ;
}


$(document).on("change", "[data-context-obj-field][data-context-table-id][type=checkbox]", function() {
    let $this = $(this);

    let table_id = $this.data("context-table-id");

    let url = get_url_update($(table_id), $this);
    let obj = get_context_obj_field($this);

    send_ajax(url, "POST", obj, table_id, update_rows_table_by_response);
});


$(document).on("change", "[data-context-obj-field][data-url-update][type=checkbox]", function() {
    let $this = $(this);

    let url = get_url_update($this, $this);
    let obj = get_context_obj_field($this);

    send_ajax(url, "POST", obj);
});


// SOURCE: https://technotrampoline.com/articles/how-to-convert-form-data-to-json-with-jquery/
function convertFormToJSON(form) {
    return $(form)
    .serializeArray()
    .reduce(
        function (json, { name, value }) {
            json[name] = value;
            return json;
        },
        {}
    );
}
