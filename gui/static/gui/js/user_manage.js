;(function () {

    var Main = {

        mixins: [BaseMixin, PermissionsMixin],
        data() {
            var validatePass = (rule, value, callback) => {
                if (value === '') {
                    callback(new Error('请输入密码'));
                } else {
                    if (this.userForm.checkPass !== '') {
                        this.$refs.userForm.validateField('checkPass');
                    }
                    callback();
                }
            };
            var validatePass2 = (rule, value, callback) => {
                if (value === '') {
                    callback(new Error('请再次输入密码'));
                } else if (value !== this.userForm.password) {
                    callback(new Error('两次输入密码不一致!'));
                } else {
                    callback();
                }
            };
            return {

                num: null,
                username: '',
                dialogCreateUserVisible: false,
                dialogEditUserVisible: false,
                tableDataUrl: PersonnelsUrl,
                userForm: {
                    username: '',
                    password: '',
                    checkPass: '',
                    num: null,
                    user_permissions: [],
                    groups: []
                },
                groups: [],
                userFormError: {
                    username: '',
                    password: '',
                    num: ''
                },
                rules: {
                    password: [
                        {validator: validatePass, trigger: 'blur'}
                    ],
                    checkPass: [
                        {validator: validatePass2, trigger: 'blur'}
                    ],
                }
            }
        },

        created: function () {

            var app = this;
            axios.get(GroupUrl + '?all=1')
                .then(function (response) {

                    app.groups = response.data.results;
                }).catch(function (error) {

            });
        },

        methods: {

            numChanged() {

                this.getFirstPage();
            },
            userNameChanged() {

                this.getFirstPage();
            },
            beforeGetData() {

                this.getParams['username'] = this.username;
                this.getParams['num'] = this.num;
            },
            clearUserForm() {

                this.userForm = {

                    username: '',
                    password: '',
                    checkPass: '',
                    num: null
                }
            },

            clearUserFormError() {

                this.userFormError = {

                    username: '',
                    password: '',
                    num: ''
                }
            },

            showCreateUserDialog() {

                this.clearUserForm();
                this.clearUserFormError();
                if (this.$refs["userForm"])
                    this.$refs["userForm"].resetFields();
                this.dialogCreateUserVisible = true;
            },

            handleCreateUser(formName) {

                this.clearUserFormError();
                var app = this;
                this.$refs[formName].validate((valid) => {
                    if (valid) {

                        axios.post(PersonnelsUrl, app.userForm)
                            .then(function (response) {

                                app.dialogCreateUserVisible = false;
                                app.$message(app.userForm.username + "创建成功");
                                app.currentChange(app.currentPage);

                            }).catch(function (error) {

                            for (const key in app.userFormError) {
                                if (error.response.data[key])
                                    app.userFormError[key] = error.response.data[key].join(",")
                            }
                        })

                    } else {

                        return false;
                    }
                });
            },

            showEditUserDialog(row) {

                this.userForm = {

                    username: '',
                    num: null,
                    user_permissions: [],
                    groups: []
                };
                this.clearUserFormError();
                this.userForm.id = row.id;
                this.userForm.username = row.username;
                this.userForm.num = row.num;
                this.userForm.user_permissions = row.user_permissions;
                this.userForm.groups = row.groups;
                this.dialogEditUserVisible = true;
            },

            handleEditUser(formName) {

                this.clearUserFormError();
                var app = this;
                this.$refs[formName].validate((valid) => {
                    if (valid) {

                        axios.put(PersonnelsUrl + app.userForm.id + '/', app.userForm)
                            .then(function (response) {

                                app.dialogEditUserVisible = false;
                                app.$message(app.userForm.username + "修改成功");
                                app.currentChange(app.currentPage);

                            }).catch(function (error) {

                            for (const key in app.userFormError) {
                                if (error.response.data[key])
                                    app.userFormError[key] = error.response.data[key].join(",")
                            }
                        })

                    } else {

                        return false;
                    }
                });
            },

            handleUserDelete: function (row) {

                var app = this;
                this.$confirm('此操作将永久删除' + row.username + ', 是否继续?', '提示', {
                    confirmButtonText: '确定',
                    cancelButtonText: '取消',
                    type: 'warning'
                }).then(() => {

                    axios.delete(PersonnelsUrl + row.id + '/')
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

            formatter(row, column) {

                return row.is_leave ? "Y" : "N"
            }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount('#app')
})();