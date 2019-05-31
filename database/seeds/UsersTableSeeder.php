<?php

use Illuminate\Database\Seeder;

class UsersTableSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        DB::table('users')->insert([
            'forename' => 'Tom',
            'middle_initials' => '',
            'surname' => 'Longridge',
            'email' => 'tomlongridge@gmail.com',
            'password' => bcrypt(' '),
            'email_verified_at' => new DateTime
        ]);
    }
}
