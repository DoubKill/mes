;(function () {

    var Main = {

        mixins: [BaseMixin, PermissionsMixin, GroupsFilterMixin],
        data: function () {

            return {
                dialogCreateGroupVisible: false,
                tableDataUrl: GroupUrl,
                groupForm: {

                    name: "",
                    group_code: "",
                    use_flag: true,
                },
                groupFormError: {

                    name: "",
                    group_code: "",
                    use_flag: "",
                },
                dialogEditGroupVisible: false,
            }
        },
        methods: {
            clearGroupForm: function () {

                this.groupForm = {

                    name: "",
                    group_code: "",
                    use_flag: true,
                }
            },
            clearGroupFormError: function () {

                this.groupFormError = {

                    name: "",
                    group_code: "",
                    use_flag: "",
                }
            },
            showCreateGroupDialog: function () {

                this.clearGroupForm();
                this.clearGroupFormError();
                this.dialogCreateGroupVisible = true;
            },
            handleCreateGroup: function () {

                this.clearGroupFormError();
                var app = this;
                axios.post(GroupUrl, app.groupForm)
                    .then(function (response) {

                        app.dialogCreateGroupVisible = false;
                        app.$message(app.groupForm.name + "创建成功");
                        app.currentChange(app.currentPage);

                    }).catch(function (error) {

                    for (var key in app.groupFormError) {
                        if (error.response.data[key])
                            app.groupFormError[key] = error.response.data[key].join(",")
                    }
                })
            },
            showEditGroupDialog: function (row) {

                this.clearGroupForm();
                this.clearGroupFormError();
                this.groupForm = Object.assign({}, row);
                this.dialogEditGroupVisible = true;
            },
            handleEditGroup: function () {

                const app = this;
                axios.put(GroupUrl + this.groupForm.id + '/', this.groupForm)
                    .then(function (response) {

                        app.dialogEditGroupVisible = false;
                        app.$message(app.groupForm.name + "修改成功");
                        app.currentChange(app.currentPage);
                    }).catch(function (error) {
                    for (var key in app.groupFormError) {

                        if (error.response.data[key])
                            app.groupFormError[key] = error.response.data[key].join(",")
                    }
                });
            },
            handleGroupDelete: function (row) {

                var app = this;
                this.$confirm('此操作将永久删除' + row.name + ', 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(() => {

                    axios.delete(GroupUrl + row.id + '/')
                        .then(function (response) {
                            app.$message({
                                type: 'success',
                                message: '删除成功!'
                            });
                            app.currentChange(app.currentPage);
                        }).catch(function (error) {

                        app.$message.error(error);
                    });


                }).catch(() => {

                });
            },
            formatter: function (row, column) {

                return row.use_flag ? "Y" : "N"
            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();