;(function () {

    var Main = {

        mixins: [BaseMixin, GroupsFilterMixin],
        data: function () {

            return {

                tableDataUrl: GroupUrl,
                groupsCurrentRow: null,
                usersByGroup: [],
                dialogAddGroupUsersDialogVisible: false,
                addGroupUsersTitle: '',
                users: [],
                selectedUsers: []
            }
        },
        created: function () {

            var app = this;
            axios.get(UsersByGroupUrl).then(function (response) {

                app.users = response.data.results;
            }).catch(function (error) {

            })
        },
        methods: {

            handleGroupsCurrentRowChange: function (row) {

                if (!row)
                    return;
                var app = this;
                this.groupsCurrentRow = row;
                axios.get(UsersByGroupUrl, {
                    params: {
                        groups: row.id
                    }
                }).then(function (response) {

                    app.usersByGroup = response.data.results;
                    console.log(response.data.results);
                    app.selectedUsers = [];
                    for (var index in app.usersByGroup) {
                        app.selectedUsers.push(app.usersByGroup[index].id);
                    }
                }).catch(function (error) {

                    this.$message.error(error);
                })
            },
            showAddGroupUsersDialog(row) {

                this.addGroupUsersTitle = "编辑" + row.name + "所属用户";
                this.dialogAddGroupUsersDialogVisible = true;
            },
            handleAddGroupUsersDialog() {

                var app = this;
                axios.put(GroupAddUserUrl + app.groupsCurrentRow.id + "/", {
                    user_set: app.selectedUsers
                }).then(function (response) {

                    app.$message(app.groupsCurrentRow.name + "修改成功");
                    app.handleGroupsCurrentRowChange(app.groupsCurrentRow);
                    app.dialogAddGroupUsersDialogVisible = false;
                }).catch(function (error) {

                });

            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();