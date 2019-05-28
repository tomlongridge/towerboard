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
            'middle_initials' => 'N',
            'surname' => 'Longridge',
            'email' => 'tomlongridge@gmail.com',
            'password' => bcrypt('password'),
            'email_verified_at' => new DateTime
        ]);
    }
}
