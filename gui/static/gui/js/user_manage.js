;(function () {

    var Main = {

        mixins: [mixin],
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

                dialogCreateUserVisible: false,
                tableDataUrl: PersonnelsUrl,
                userForm: {
                    username: '',
                    password: '',
                    checkPass: '',
                    num: null
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

        methods: {

            showCreateUserDialog() {

                this.dialogCreateUserVisible = true;
            },
            submitForm(formName) {

                var app = this;
                this.$refs[formName].validate((valid) => {
                    if (valid) {

                        axios.post(PersonnelsUrl, app.userForm)
                            .then(function (response) {

                                app.dialogCreateUserVisible = false;
                                app.$message(app.userForm.username + "创建成功");
                                app.currentChange(app.currentPage);

                            }).catch(function (error) {


                        })

                    } else {

                        return false;
                    }
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