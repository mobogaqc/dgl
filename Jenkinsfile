pipeline {
    agent none
    stages {
        stage('Build and Test') {
            parallel {
                stage('CPU') {
                    agent {
                        docker {
                            image 'lingfanyu/dgl-cpu'
                            args '-u root'
                        }
                    }
                    stages {
                        stage('SETUP') {
                            steps {
                                sh 'easy_install nose'
                                sh 'git submodule init'
                                sh 'git submodule update'
                            }
                        }
                        stage('BUILD') {
                            steps {
                                sh 'if [ -d build ]; then rm -rf build; fi; mkdir build'
                                dir('python') {
                                    sh 'python3 setup.py install'
                                }
                                dir ('build') {
                                    sh 'cmake ..'
                                    sh 'make -j$(nproc)'
                                }
                            }
                        }
                        stage('TEST') {
                            steps {
                                withEnv(["DGL_LIBRARY_PATH=${env.WORKSPACE}/build"]) {
                                    sh 'echo $DGL_LIBRARY_PATH'
                                    sh 'nosetests tests -v --with-xunit'
                                    sh 'nosetests tests/pytorch -v --with-xunit'
                                }
                            }
                        }
                    }
                    post {
                        always {
                            junit '*.xml'
                        }
                    }
                }
                stage('GPU') {
                    agent {
                        docker {
                            image 'lingfanyu/dgl-gpu'
                            args '--runtime nvidia -u root'
                        }
                    }
                    stages {
                        stage('SETUP') {
                            steps {
                                sh 'easy_install nose'
                                sh 'git submodule init'
                                sh 'git submodule update'
                            }
                        }
                        stage('BUILD') {
                            steps {
                                sh 'if [ -d build ]; then rm -rf build; fi; mkdir build'
                                dir('python') {
                                    sh 'python3 setup.py install'
                                }
                                dir ('build') {
                                    sh 'cmake ..'
                                    sh 'make -j$(nproc)'
                                }
                            }
                        }
                        stage('TEST') {
                            steps {
                                withEnv(["DGL_LIBRARY_PATH=${env.WORKSPACE}/build"]) {
                                    sh 'echo $DGL_LIBRARY_PATH'
                                    sh 'nosetests tests -v --with-xunit'
                                    sh 'nosetests tests/pytorch -v --with-xunit'
                                }
                            }
                        }
                    }
                    post {
                        always {
                            junit '*.xml'
                        }
                    }
                }
            }
        }
    }
}
